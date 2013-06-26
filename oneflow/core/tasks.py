# -*- coding: utf-8 -*-

import time
import redis
import logging
import datetime
from constance import config

from humanize.time import naturaldelta, naturaltime

from pymongo.errors import DuplicateKeyError
from libgreader import GoogleReader, OAuth2Method
from libgreader.url import ReaderUrl

from celery import task

from django.conf import settings
from django.core.mail import mail_admins
from django.contrib.auth import get_user_model

from .models import RATINGS
from .models.nonrel import Article, Feed, Subscription, Read, User as MongoUser
from .gr_import import GoogleReaderImport

#from ..base.utils import send_email_with_db_content

# We don't fetch articles too far in the past, even if google has them.
GR_OLDEST_DATE = datetime.datetime(2008, 1, 1, 0, 0)

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=getattr(settings, 'MAIN_SERVER',
                          'localhost'), port=6379,
                          db=getattr(settings, 'REDIS_DB', 0))

User = get_user_model()

ftstamp = datetime.datetime.fromtimestamp
now     = datetime.datetime.now
today   = datetime.date.today


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
    except DuplicateKeyError:
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


def create_article_and_read(gr_article, gr_feed, feed, mongo_user):

    #LOGGER.info(u'Importing article “%s” from feed “%s” (%s/%s, wave %s)…',
    #     gr_article.title, gr_feed.title, articles_counter, total, wave + 1)

    try:
        Article.objects(url=gr_article.url).update_one(
            set__url=gr_article.url, set__title=gr_article.title,
            set__feed=feed, set__content=gr_article.content,
            set__google_reader_original_data=gr_article.data, upsert=True)

    except DuplicateKeyError:
        LOGGER.warning(u'Duplicate article “%s” in feed “%s”: DATA=%s',
                       gr_article.title, feed.name, gr_article.data)

    article = Article.objects.get(url=gr_article.url)
    tags = [c.label for c in gr_feed.getCategories()]

    Read.objects(article=article,
                 user=mongo_user
                 ).update(set__article=article,
                          set__user=mongo_user,
                          set__tags=tags,
                          set__is_read=gr_article.read,
                          set__date_created=ftstamp(gr_article.time),
                          set__rating=article.default_rating +
                          (RATINGS.STARRED if gr_article.starred
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

    gri.reg_date(time.mktime(reg_date.timetuple()))
    gri.star1_date(time.mktime(star1_date.timetuple()))
    gri.total_reads(total_reads)
    gri.total_starred(total_starred)

    LOGGER.info(u'Google Reader import: %s feed(s) and %s read '
                u'article(s) to go…', total_feeds, total_reads)

    if total_feeds > GR_MAX_FEEDS and not settings.DEBUG:
        mail_admins('User {0} has more than {1} feeds: {2}!'.format(
                    username, GR_MAX_FEEDS, total_feeds),
                    u"\n\nThe GR import will be incomplete.\n\n"
                    u"Just for you to know…\n\n")

    # We need to clamp the total, else task won't finish in
    # the case where the user has more feeds than allowed.
    gri.total_feeds(min(total_feeds, GR_MAX_FEEDS))

    # We launch the starred feed import first. Launching it after the
    # standard feeds makes it being delayed until the world's end.
    reader.makeSpecialFeeds()
    starred_feed = reader.getSpecialFeed(ReaderUrl.STARRED_LIST)
    import_google_reader_starred.apply_async((user_id, username, starred_feed),
                                             queue='low')

    processed_feeds = 1

    for gr_feed in reader.feeds[:GR_MAX_FEEDS]:

        LOGGER.info(u'Importing feed “%s” (%s/%s)…',
                    gr_feed.title, processed_feeds + 1, total_feeds)

        feed = create_feed(gr_feed, mongo_user)

        # go to default queue.
        import_google_reader_articles.apply_async(
            (user_id, username, gr_feed, feed), queue='low')

        processed_feeds += 1

    LOGGER.info(u'Imported %s feeds in %s. Articles import already '
                u'started with limits: date: %s, %s waves of %s articles, '
                u'max articles: %s, reads: %s, starred: %s.',
                processed_feeds, naturaldelta(now() - gri.start()),
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

    try:
        loadMethod(loadLimit=config.GR_LOAD_LIMIT)

    except:
        LOGGER.exception(u'Wave %s of feed “%s” failed to load for user %s, '
                         u'aborted.', wave, gr_feed.title, username)
        gri.incr_feeds()
        return

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
        feed = create_feed(real_gr_feed, mongo_user, subscription=subscribed)

        create_article_and_read(gr_article, real_gr_feed, feed, mongo_user)

        if not subscribed:
            gri.incr_articles()

        if gr_article.read:
            gri.incr_reads()

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

    try:
        loadMethod(loadLimit=config.GR_LOAD_LIMIT)

    except:
        LOGGER.exception(u'Wave %s of feed “%s” failed to load for user %s, '
                         u'aborted.', wave, gr_feed.title, username)
        gri.incr_feeds()
        return

    total            = len(gr_feed.items)
    articles_counter = 0

    for gr_article in gr_feed.items:

        if end_fetch_prematurely('reads', gri, articles_counter,
                                 gr_article, gr_feed.title, username,
                                 hard_limit, date_limit=date_limit):
            return

        # Read articles are always imported
        if gr_article.read:
            create_article_and_read(gr_article, gr_feed, feed, mongo_user)
            gri.incr_articles()
            gri.incr_reads()

        # Unread articles are imported only if there is room for them.
        elif gri.articles() < (hard_limit - gri.reads()):
            create_article_and_read(gr_article, gr_feed, feed, mongo_user)
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


@task
def clean_obsolete_redis_keys():
    """ Call in turn all redis-related cleaners. """

    if today() <= (config.GR_END_DATE + datetime.timedelta(days=1)):
        clean_gri_keys()
