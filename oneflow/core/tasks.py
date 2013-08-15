# -*- coding: utf-8 -*-

import redis
import logging
import time as pytime

from random import randrange
from constance import config

from pymongo.errors import DuplicateKeyError
from mongoengine.errors import OperationError, NotUniqueError, ValidationError
from mongoengine.queryset import Q

from libgreader import GoogleReader, OAuth2Method
from libgreader.url import ReaderUrl

from celery import task

from django.conf import settings
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from django.core.mail import mail_managers
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from .models import (RATINGS,
                     Article, Feed, Subscription, Read, User as MongoUser)
from .stats import synchronize_statsd_articles_gauges

from .gr_import import GoogleReaderImport

from ..base.utils import RedisExpiringLock
from ..base.utils.dateutils import (now, ftstamp, today, timedelta, datetime,
                                    naturaldelta, naturaltime, benchmark)

# We don't fetch articles too far in the past, even if google has them.
GR_OLDEST_DATE = datetime(2008, 1, 1)

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=settings.REDIS_HOST,
                          port=settings.REDIS_PORT,
                          db=settings.REDIS_DB)

User = get_user_model()


def get_user_from_dbs(user_id):
    django_user = User.objects.get(id=user_id)
    MongoUser.objects(django_user=django_user.id
                      ).update_one(set__django_user=django_user.id,
                                   upsert=True)

    return django_user, MongoUser.objects.get(django_user=django_user.id)


def import_google_reader_trigger(user_id, refresh=False):
    """ This function allow to trigger the celery task from anywhere.
        just pass it a user ID. It's called from the views, and we created
        it to deal whith `access_token`-related errors before launching
        the real task.

        Without doing like this, the error would happen in the remote
        celery task and we would not be aware of it in the django views.
    """

    user = User.objects.get(id=user_id)

    if refresh:
        # See http://django-social-auth.readthedocs.org/en/latest/use_cases.html#token-refreshing # NOQA
        LOGGER.warning(u'Refreshing invalid access_token for user %s.',
                       user.username)

        social = user.social_auth.get(provider='google-oauth2')
        social.refresh_token()

    # Try to get the token. If this fails, the caller will
    # catch the exception and will notify the user.
    access_token = user.social_auth.get(
        provider='google-oauth2').tokens['access_token']

    # notify the start, to instantly refresh user
    # home and admin interface lists upon reload.
    GoogleReaderImport(user_id).start(set_time=True)

    # Go to high-priority queue to allow parallel processing
    import_google_reader_begin.apply_async((user_id, access_token),
                                           queue='high')


def create_feed(gr_feed, mongo_user, subscription=True):

    try:
        Feed.objects(url=gr_feed.feedUrl,
                     site_url=gr_feed.siteUrl
                     ).update(set__url=gr_feed.feedUrl,
                              set__site_url=gr_feed.siteUrl,
                              set__name=gr_feed.title,
                              upsert=True)

    except (OperationError, DuplicateKeyError):
        LOGGER.warning(u'Duplicate feed “%s”, skipped insertion.',
                       gr_feed.title)

    feed = Feed.objects.get(url=gr_feed.feedUrl, site_url=gr_feed.siteUrl)

    if subscription:
        tags = [c.label for c in gr_feed.getCategories()]

        Subscription.objects(feed=feed,
                             user=mongo_user
                             ).update(set__feed=feed,
                                      set__user=mongo_user,
                                      set__tags=tags,
                                      upsert=True)

    return feed


def create_article_and_read(article_url,
                            article_title, article_content,
                            article_time, article_data,
                            feed, mongo_users, is_read, is_starred,
                            categories):
    #LOGGER.info(u'Importing article “%s” from feed “%s” (%s/%s, wave %s)…',
    #     gr_article.title, gr_feed.title, articles_counter, total, wave + 1)

    try:
        Article.objects(url=article_url).update_one(
            set__url=article_url, set__title=article_title,
            add_to_set__feeds=feed, set__content=article_content,
            set__date_published=None
                if article_time is None
                else ftstamp(article_time),
            set__google_reader_original_data=article_data, upsert=True)

    except (OperationError, DuplicateKeyError):
        LOGGER.warning(u'Duplicate article “%s” (url: %s) in feed “%s”: '
                       u'DATA=%s', article_title, article_url, feed.name,
                       article_data)

    try:
        article = Article.objects.get(url=article_url)

    except Article.DoesNotExist:
        LOGGER.error(u'Article “%s” (url: %s) in feed “%s” upsert failed: '
                     u'DATA=%s', article_title[:40]
                     + (article_title[:40] and u'…'),
                     article_url[:40] + (article_url[:40] and u'…'),
                     feed.name, article_data)
        return

    for mongo_user in mongo_users:
        Read.objects(article=article,
                     user=mongo_user
                     ).update(set__article=article,
                              set__user=mongo_user,
                              set__tags=categories,
                              set__is_read=is_read,
                              set__rating=article.default_rating +
                              (RATINGS.STARRED if is_starred
                               else 0.0),
                              upsert=True)


def end_fetch_prematurely(kind, gri, processed, gr_article, gr_feed_title,
                          username, hard_articles_limit, date_limit=None):

    if not gri.running():
        # Everything is stopped. Just return. Either the admin
        # stopped manually, or we reached a hard limit.
        gri.incr_feeds()
        return True

    if kind == 'reads' and gri.reads() >= gri.total_reads():
        LOGGER.info(u'All read articles imported for user %s.', username)
        gri.incr_feeds()
        return True

    if kind == 'starred' and gri.starred() >= gri.total_starred():
        LOGGER.info(u'All starred articles imported for user %s.', username)
        gri.incr_feeds()
        return True

    if gri.articles() >= hard_articles_limit:
        LOGGER.info(u'Reached hard storage limit for user %s, stopping '
                    u'import of feed “%s”.', username, gr_feed_title)
        gri.incr_feeds()
        return True

    if date_limit:
        if gr_article.time is None:
            LOGGER.warning(u'Article %s (feed “%s”, user %s) has no time. '
                           u'DATA=%s.', gr_article, gr_feed_title,
                           username, gr_article.time, gr_article.data)

        else:
            if ftstamp(gr_article.time) < date_limit:
                LOGGER.warning(u'Datetime limit reached on feed “%s” '
                               u'for user %s, stopping. %s article(s) '
                               u'imported.', gr_feed_title,
                               username, processed)
                # We could (or not) have reached all the read items
                # in this feed. In case we don't, incr() feeds will
                # ensure the whole import will stop if all feeds
                # reach their date limit (or end by lack of items).
                gri.incr_feeds()
                return True

    return False


def end_task_or_continue_fetching(gri, total, wave,
                                  gr_feed_title, username,
                                  task_to_call, task_args, task_kwargs):

    if not gri.running():
        gri.incr_feeds()
        return True

    # We use ">" (not just "==") in case the limit was lowered
    # by the administrators during the current run.
    if total >= config.GR_LOAD_LIMIT:
        # Reaching the load limit means “Go for next wave”, because
        # there is probably more articles. We have to fetch to see.

        if wave < config.GR_WAVE_LIMIT:
            task_to_call.delay(*task_args, **task_kwargs)

            LOGGER.info(u'Wave %s imported %s articles of '
                        u'feed “%s” for user %s, continuing.', wave, total,
                        gr_feed_title, username)

        else:
            LOGGER.warning(u'Wave limit reached on feed “%s”, for user '
                           u'%s, stopping.', gr_feed_title, username)
            # Notify we are out of luck.
            gri.incr_feeds()
            return True
    else:
        # We have reached the "beginning" of the feed in GR.
        # Probably one with only a few subscribers, because
        # in normal conditions, GR data is virtually unlimited.
        LOGGER.info(u'Reached beginning of feed “%s” for user %s, %s '
                    u'article(s) imported.', gr_feed_title, username, total)
        gri.incr_feeds()
        return True

    return False


def empty_gr_feed(gr_feed):
    """ Remove processed items from the feed.

        Having removed them here adds the benefit of
        not storing them in the celery queue :-)
    """

    # Remove the read items before loading more
    # else we leak much too much too muuuuuch…
    gr_feed.items[:] = []

    # Avoid keeping strong references too…
    gr_feed.itemsById = {}


@task
def import_google_reader_begin(user_id, access_token):

    auth = OAuth2Method(settings.GOOGLE_OAUTH2_CLIENT_ID,
                        settings.GOOGLE_OAUTH2_CLIENT_SECRET)
    auth.authFromAccessToken(access_token)
    reader = GoogleReader(auth)

    django_user, mongo_user = get_user_from_dbs(user_id)
    username = django_user.username

    try:
        user_infos = reader.getUserInfo()

    except TypeError:
        LOGGER.exception(u'Could not start Google Reader import for user %s.',
                         username)
        # Don't refresh, it's now done by a dedicated periodic task.
        # If we failed, it means the problem is quite serious.
        #       import_google_reader_trigger(user_id, refresh=True)
        return

    GR_MAX_FEEDS = config.GR_MAX_FEEDS

    LOGGER.info(u'Starting Google Reader import for user %s.', username)

    gri = GoogleReaderImport(user_id)

    # take note of user informations now that we have them.
    gri.start(user_infos=user_infos)

    reader.buildSubscriptionList()

    total_reads, reg_date     = reader.totalReadItems(without_date=False)
    total_starred, star1_date = reader.totalStarredItems(without_date=False)
    total_feeds               = len(reader.feeds) + 1  # +1 for 'starred'

    gri.reg_date(pytime.mktime(reg_date.timetuple()))
    gri.star1_date(pytime.mktime(star1_date.timetuple()))
    gri.total_reads(total_reads)
    gri.total_starred(total_starred)

    LOGGER.info(u'Google Reader import for user %s: %s feed(s) and %s read '
                u'article(s) to go…', username, total_feeds, total_reads)

    if total_feeds > GR_MAX_FEEDS and not settings.DEBUG:
        mail_admins('User {0} has more than {1} feeds: {2}!'.format(
                    username, GR_MAX_FEEDS, total_feeds),
                    u"\n\nThe GR import will be incomplete.\n\n"
                    u"Just for you to know…\n\n")

    # We launch the starred feed import first. Launching it after the
    # standard feeds makes it being delayed until the world's end.
    reader.makeSpecialFeeds()
    starred_feed = reader.getSpecialFeed(ReaderUrl.STARRED_LIST)
    import_google_reader_starred.apply_async((user_id, username, starred_feed),
                                             queue='low')

    processed_feeds = 1
    feeds_to_import = []

    for gr_feed in reader.feeds[:GR_MAX_FEEDS]:

        try:
            feed = create_feed(gr_feed, mongo_user)

        except Feed.DoesNotExist:
            LOGGER.exception(u'Could not create feed “%s” for user %s, '
                             u'skipped.', gr_feed.title, username)
            continue

        processed_feeds += 1
        feeds_to_import.append((user_id, username, gr_feed, feed))

        LOGGER.info(u'Imported feed “%s” (%s/%s) for user %s…',
                    gr_feed.title, processed_feeds, total_feeds, username)

    # We need to clamp the total, else task won't finish in
    # the case where the user has more feeds than allowed.
    #
    gri.total_feeds(min(processed_feeds, GR_MAX_FEEDS))

    for feed_args in feeds_to_import:
        import_google_reader_articles.apply_async(feed_args, queue='low')

    LOGGER.info(u'Imported %s/%s feeds in %s. Articles import already '
                u'started with limits: date: %s, %s waves of %s articles, '
                u'max articles: %s, reads: %s, starred: %s.',
                processed_feeds, total_feeds,
                naturaldelta(now() - gri.start()),
                naturaltime(max([gri.reg_date(), GR_OLDEST_DATE])),
                config.GR_WAVE_LIMIT, config.GR_LOAD_LIMIT,
                config.GR_MAX_ARTICLES, total_reads, total_starred)


@task
def import_google_reader_starred(user_id, username, gr_feed, wave=0):

    mongo_user = MongoUser.objects.get(django_user=user_id)
    gri        = GoogleReaderImport(user_id)
    date_limit = max([gri.reg_date(), GR_OLDEST_DATE])
    hard_limit = config.GR_MAX_ARTICLES

    if not gri.running():
        # In case the import was stopped while this task was stuck in the
        # queue, just stop now. As we return, it's one more feed processed.
        gri.incr_feeds()
        return

    loadMethod = gr_feed.loadItems if wave == 0 else gr_feed.loadMoreItems

    retry = 0

    while True:
        try:
            loadMethod(loadLimit=config.GR_LOAD_LIMIT)

        except:
            if retry < config.GR_MAX_RETRIES:
                LOGGER.warning(u'Wave %s (try %s) of feed “%s” failed to load '
                               u'for user %s, retrying…', wave, retry,
                               gr_feed.title, username)
                pytime.sleep(5)
                retry += 1

            else:
                LOGGER.exception(u'Wave %s of feed “%s” failed to load for '
                                 u'user %s, after %s retries, aborted.', wave,
                                 gr_feed.title, username, retry)
                gri.incr_feeds()
                return
        else:
            break

    total            = len(gr_feed.items)
    articles_counter = 0

    for gr_article in gr_feed.items:
        if end_fetch_prematurely('starred', gri, articles_counter,
                                 gr_article, gr_feed.title, username,
                                 hard_limit, date_limit=date_limit):
            return

        # Get the origin feed, the "real" one.
        # because currently gr_feed = 'starred',
        # which is a virtual one without an URL.
        real_gr_feed = gr_article.feed
        subscribed   = real_gr_feed in gr_feed.googleReader.feeds

        try:
            feed = create_feed(real_gr_feed, mongo_user,
                               subscription=subscribed)

        except Feed.DoesNotExist:
            LOGGER.exception(u'Could not create feed “%s” (from starred) for '
                             u'user %s, skipped.', real_gr_feed.title, username)

            # We increment anyway, else the import will not finish.
            # TODO: We should decrease the starred total instead.
            gri.incr_starred()
            continue

        create_article_and_read(gr_article.url, gr_article.title,
                                gr_article.content,
                                gr_article.time, gr_article.data,
                                feed, [mongo_user], gr_article.read,
                                gr_article.starred,
                                [c.label for c
                                in real_gr_feed.getCategories()])

        if not subscribed:
            gri.incr_articles()

        # starred don't implement reads. Not perfect, not
        # accurate, but no time for better implementation.
        #if gr_article.read:
        #    gri.incr_reads()
        gri.incr_starred()

    empty_gr_feed(gr_feed)

    end_task_or_continue_fetching(gri, total, wave,
                                  gr_feed.title, username,
                                  import_google_reader_starred,
                                  (user_id, username, gr_feed),
                                  {'wave': wave + 1})


@task
def import_google_reader_articles(user_id, username, gr_feed, feed, wave=0):

    mongo_user = MongoUser.objects.get(django_user=user_id)
    gri        = GoogleReaderImport(user_id)
    date_limit = max([gri.reg_date(), GR_OLDEST_DATE])
    # Be sure all starred articles can be fetched.
    hard_limit = config.GR_MAX_ARTICLES - gri.total_starred()

    if not gri.running():
        # In case the import was stopped while this task was stuck in the
        # queue, just stop now. As we return, it's one more feed processed.
        gri.incr_feeds()
        return

    loadMethod = gr_feed.loadItems if wave == 0 else gr_feed.loadMoreItems

    retry = 0

    while True:
        try:
            loadMethod(loadLimit=config.GR_LOAD_LIMIT)

        except:
            if retry < config.GR_MAX_RETRIES:
                LOGGER.warning(u'Wave %s (try %s) of feed “%s” failed to load '
                               u'for user %s, retrying…', wave, retry,
                               gr_feed.title, username)
                pytime.sleep(5)
                retry += 1

            else:
                LOGGER.exception(u'Wave %s of feed “%s” failed to load for '
                                 u'user %s, after %s retries, aborted.', wave,
                                 gr_feed.title, username, retry)
                gri.incr_feeds()
                return
        else:
            break

    total            = len(gr_feed.items)
    articles_counter = 0

    categories = [c.label for c in gr_feed.getCategories()]

    for gr_article in gr_feed.items:

        if end_fetch_prematurely('reads', gri, articles_counter,
                                 gr_article, gr_feed.title, username,
                                 hard_limit, date_limit=date_limit):
            return

        # Read articles are always imported
        if gr_article.read:
            create_article_and_read(gr_article.url, gr_article.title,
                                    gr_article.content,
                                    gr_article.time, gr_article.data,
                                    feed, [mongo_user], gr_article.read,
                                    gr_article.starred,
                                    categories)
            gri.incr_articles()
            gri.incr_reads()

        # Unread articles are imported only if there is room for them.
        elif gri.articles() < (hard_limit - gri.reads()):
            create_article_and_read(gr_article.url, gr_article.title,
                                    gr_article.content,
                                    gr_article.time, gr_article.data,
                                    feed, [mongo_user], gr_article.read,
                                    gr_article.starred,
                                    categories)
            gri.incr_articles()

        articles_counter += 1

    empty_gr_feed(gr_feed)

    end_task_or_continue_fetching(gri, total, wave,
                                  gr_feed.title, username,
                                  import_google_reader_articles,
                                  (user_id, username, gr_feed, feed),
                                  {'wave': wave + 1})


def clean_gri_keys():
    """ Remove all GRI obsolete keys. """

    keys = REDIS.keys('gri:*:run')

    users_ids = [x[0] for x in User.objects.all().values_list('id')]

    for key in keys:
        user_id = int(key.split(':')[1])

        if user_id in users_ids:
            continue

        name = u'gri:%s:*' % user_id
        LOGGER.info(u'Deleting obsolete redis keys %s…' % name)
        names = REDIS.keys(name)
        REDIS.delete(*names)


@task(queue='medium')
def clean_obsolete_redis_keys():
    """ Call in turn all redis-related cleaners. """

    start_time = pytime.time()

    if today() <= (config.GR_END_DATE + timedelta(days=1)):
        clean_gri_keys()

    LOGGER.info(u'clean_obsolete_redis_keys(): finished in %s.',
                naturaldelta(pytime.time() - start_time))

# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Refresh RSS feeds


@task(queue='high')
def refresh_all_feeds(limit=None):

    if config.FEED_FETCH_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Feed refresh disabled in configuration.')
        return

    # Be sure two refresh operations don't overlap, but don't hold the
    # lock too long if something goes wrong. In production conditions
    # as of 20130812, refreshing all feeds takes only a moment:
    # [2013-08-12 09:07:02,028: INFO/MainProcess] Task
    #       oneflow.core.tasks.refresh_all_feeds succeeded in 1.99886608124s.
    my_lock = RedisExpiringLock('refresh_all_feeds', expire_time=120)

    if not my_lock.acquire():
        # Avoid running this task over and over again in the queue
        # if the previous instance did not yet terminate. Happens
        # when scheduled task runs too quickly.
        LOGGER.warning(u'refresh_all_feeds() is already locked, aborting.')
        return

    feeds = Feed.objects.filter(closed__ne=True)

    if limit:
        feeds = feeds.limit(limit)

    # No need for caching and cluttering CPU/memory for a one-shot thing.
    feeds.no_cache()

    with benchmark('refresh_all_feeds()'):

        count = 0
        mynow = now()

        for feed in feeds:
            interval = timedelta(seconds=feed.fetch_interval)

            if feed.last_fetch is None:

                feed.refresh.delay()

                LOGGER.info(u'Launched immediate refresh of feed %s which '
                            u'has never been refreshed.', feed)

            elif feed.last_fetch + interval < mynow:

                how_late = feed.last_fetch + interval - mynow
                how_late = how_late.days * 86400 + how_late.seconds

                #LOGGER.warning('>> %s %s < %s: %s', feed.id,
                #               feed.last_fetch + interval, mynow, how_late)

                if config.FEED_REFRESH_RANDOMIZE:
                    countdown = randrange(config.FEED_REFRESH_RANDOMIZE_DELAY)
                    feed.refresh.apply_async((), countdown=countdown)

                else:
                    countdown = 0
                    feed.refresh.delay()

                LOGGER.info(u'%s refresh of feed %s %s (%s late).',
                            u'Scheduled randomized'
                            if countdown else u'Launched',
                            feed,
                            u' in {0}'.format(naturaldelta(countdown))
                            if countdown else u'in the background',
                            naturaldelta(how_late))
                count += 1

        LOGGER.info(u'Launched %s refreshes out of %s feed(s) checked.',
                    count, feeds.count())

    my_lock.release()


@task(queue='high')
def global_feeds_checker():

    dtnow        = now()
    limit_days   = config.FEED_CLOSED_WARN_LIMIT
    closed_limit = dtnow - timedelta(days=limit_days)

    feeds = Feed.objects(Q(closed=True)
                         & (Q(date_closed__exists=False)
                            | Q(date_closed__gte=closed_limit)))

    count = feeds.count()

    if count > 10000:
        # prevent CPU and memory hogging.
        LOGGER.info(u'Switching query to no_cache(), this will take longer.')
        feeds.no_cache()

    if not count:
        LOGGER.info('No feed was closed in the last %s days.', limit_days)
        return

    mail_managers(_(u'Reminder: {0} feed(s) closed in last '
                  u'{1} day(s)').format(count, limit_days),
                  _(u"\n\nHere is the list, dates (if any), and reasons "
                  u"(if any) of closing:\n\n{feed_list}\n\nYou can manually "
                  u"reopen any of them from the admin interface.\n\n").format(
                  feed_list='\n\n'.join(
                  u'- %s,\n'
                  u'    - admin url: http://%s%s\n'
                  u'    - public url: %s\n'
                  u'    - %s\n'
                  u'    - reason: %s\n'
                  u'    - last error: %s' % (
                      feed,
                      settings.SITE_DOMAIN,
                      reverse('admin:%s_%s_change' % (
                          feed._meta.get('app_label', 'models'),
                          feed._meta.get('module_name', 'feed')),
                          args=[feed.id]),
                      feed.url,
                      (u'closed on %s' % feed.date_closed)
                          if feed.date_closed else u'(no closing date)',
                      feed.closed_reason or
                          u'none (or manually closed from the admin interface)',
                      feed.errors[0] if len(feed.errors)
                          else u'(no error recorded)')
                  for feed in feeds)))

    start_time = pytime.time()

    # Close the feeds, but after sending the mail,
    # So that initial reason is displayed at least
    # once to a real human.
    for feed in feeds:
        if feed.date_closed is None:
            feed.close('Automatic close by periodic checker task')

    LOGGER.info('Closed %s feeds in %s.', count,
                naturaldelta(pytime.time() - start_time))


# ••••••••••••••••••••••••••••••••••••••••••••••••••• Move things to Archive DB

def archive_article_one_internal(article, counts):
    """ internal function. Do not use directly
        unless you know what you're doing. """

    delete_anyway = True
    article.switch_db('archive')

    try:
        article.save()

    except (NotUniqueError, DuplicateKeyError):
        counts['archived_dupes'] += 1

    except ValidationError:
        # If the article doesn't validate in the archive database, how
        # the hell did it make its way into the production one?? Perhaps
        # a scoria of the GR import which did update_one(set_*…), which
        # bypassed the validation phase.
        # Anyway, beiing here means the article is duplicate or orphaned.
        # So just forget the validation error and wipe it from production.
        LOGGER.exception(u'Article archiving failed for %s', article)
        counts['bad_articles'] += 1

    except:
        delete_anyway = False

    if delete_anyway:
        article.switch_db('default')
        article.delete()


@task(queue='medium')
def archive_articles(limit=None):

    counts = {
        'duplicates': 0,
        'orphaned': 0,
        'bad_articles': 0,
        'archived_dupes': 0,
    }

    if limit is None:
        limit = config.ARTICLE_ARCHIVE_BATCH_SIZE

    duplicates = Article.objects(duplicate_of__ne=None).limit(limit).no_cache()
    orphaned   = Article.objects(orphaned=True).limit(limit).no_cache()

    counts['duplicates'] = duplicates.count()
    counts['orphaned']   = orphaned.count()

    if counts['duplicates']:
        with benchmark('Archiving of %s duplicate article(s)'
                       % counts['duplicates']):
            for article in duplicates:
                archive_article_one_internal(article, counts)

    if counts['orphaned']:
        with benchmark('Archiving of %s orphaned article(s)'
                       % counts['orphaned']):
            for article in orphaned:
                archive_article_one_internal(article, counts)

    if counts['duplicates'] or counts['orphaned']:
        synchronize_statsd_articles_gauges(full=True)

        LOGGER.info('%s already archived and %s bad articles were found '
                    u'during the operation.', counts['archived_dupes'],
                    counts['bad_articles'])

    else:
        LOGGER.info(u'No article to archive.')


@task(queue='medium')
def archive_documents(limit=None):

    # these are tasks, but we run them sequentially in this global archive job
    # to avoid hammering the production database with multiple archive jobs.
    archive_articles(limit=limit)
