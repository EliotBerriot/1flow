# -*- coding: utf-8 -*-

import time
import logging
import datetime
from constance import config

from humanize.time import naturaldelta, naturaltime

from pymongo.errors import DuplicateKeyError
from libgreader import GoogleReader, OAuth2Method

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
User = get_user_model()


def get_user_from_dbs(user_id):
    django_user = User.objects.get(id=user_id)
    MongoUser.objects(django_user=django_user.id
                      ).update_one(set__django_user=django_user.id,
                                   upsert=True)

    return django_user, MongoUser.objects.get(django_user=django_user.id)


def import_google_reader_data_trigger(user_id):
    """ This function allows to trigger the task manually,
        just pass it a user ID. It's called from the views, and we separate it
        to allow catching the access_token related errors in there.

        Without doing like this, the error will happen in the remote celery
        task and we are not aware of it in the django view.
    """

    user = User.objects.get(id=user_id)

    # Try to get the token. If this fails, the caller will
    # catch the exception and will notify the user.
    user.social_auth.get(
        provider='google-oauth2').tokens['access_token']

    gri = GoogleReaderImport(user.id)

    # notify it will start, to avoid the
    # import button showing again on web page.
    gri.start(set_time=True)

    # go to high-priority queue.
    import_google_reader_data.apply_async((user_id, ), queue='high')


@task
def import_google_reader_data(user_id):

    now = datetime.datetime.now

    GR_MAX_FEEDS = config.GR_MAX_FEEDS

    django_user, mongo_user = get_user_from_dbs(user_id)

    access_token = django_user.social_auth.get(
        provider='google-oauth2').tokens['access_token']

    auth = OAuth2Method(settings.GOOGLE_OAUTH2_CLIENT_ID,
                        settings.GOOGLE_OAUTH2_CLIENT_SECRET)
    auth.authFromAccessToken(access_token)
    reader = GoogleReader(auth)

    try:
        user_infos = reader.getUserInfo()

    except TypeError:
        # See http://django-social-auth.readthedocs.org/en/latest/use_cases.html#token-refreshing # NOQA
        social = django_user.social_auth.get(provider='google-oauth2')
        social.refresh_token()

        import_google_reader_data.delay(user_id)
        LOGGER.warning('Restarted Google Reader import for user %s, '
                       'access_token was invalid.', django_user.username)
        return

    LOGGER.info('Starting Google Reader import for user %s(%s)',
                user_infos['userEmail'], user_infos['userId'])

    gri = GoogleReaderImport(django_user.id)

    # take note of user informations now that we have them.
    gri.start(user_infos=user_infos)

    reader.buildSubscriptionList()

    total_reads, gr_register_date = reader.totalReadItems(without_date=False)

    total_feeds     = len(reader.feeds)
    processed_feeds = 0

    gri.reg_date(time.mktime(gr_register_date.timetuple()))
    gri.total_reads(total_reads)
    gri.total_feeds(total_feeds)

    LOGGER.info(u'Google Reader import: %s feed(s) and %s read '
                u'article(s) to go…', total_feeds, total_reads)

    if total_feeds > GR_MAX_FEEDS and not settings.DEBUG:
        mail_admins('User {0} has more than {1} feeds: {2}!'.format(
                    django_user.username, GR_MAX_FEEDS, total_feeds), """

The GR import will be incomplete.

Just for you to know…
""")

    for gr_feed in reader.feeds[:GR_MAX_FEEDS]:

        LOGGER.info(u'Importing feed “%s” (%s/%s)…',
                    gr_feed.title, processed_feeds + 1, total_feeds)

        Feed.objects(url=gr_feed.feedUrl,
                     site_url=gr_feed.siteUrl
                     ).update(set__url=gr_feed.feedUrl,
                              set__site_url=gr_feed.siteUrl,
                              set__name=gr_feed.title,
                              upsert=True)

        feed = Feed.objects.get(url=gr_feed.feedUrl, site_url=gr_feed.siteUrl)
        tags = [c.label for c in gr_feed.getCategories()]

        Subscription.objects(feed=feed,
                             user=mongo_user
                             ).update(set__feed=feed,
                                      set__user=mongo_user,
                                      set__tags=tags,
                                      upsert=True)

        # go to default queue.
        import_google_reader_articles.apply_async(
            (user_id, gr_feed, feed), queue='low')

        processed_feeds += 1
        gri.incr_feeds()

    LOGGER.info(u'Done importing %s feeds in %s; articles import already '
                u'started with limits. Date: %s, max waves: %s or %s '
                u'articles, total max articles: %s, max reads: %s.',
                processed_feeds, naturaldelta(now() - gri.start()),
                naturaltime(max([gri.reg_date(), GR_OLDEST_DATE])),
                config.GR_WAVE_LIMIT, config.GR_LOAD_LIMIT,
                config.GR_MAX_ARTICLES, total_reads)


@task
def import_google_reader_articles(user_id, gr_feed, feed, wave=0):

    ftstamp = datetime.datetime.fromtimestamp

    # Get them right here so we don't hit redis at each loop-cycle.
    GR_LOAD_LIMIT   = config.GR_LOAD_LIMIT
    GR_MAX_ARTICLES = config.GR_MAX_ARTICLES

    django_user, mongo_user = get_user_from_dbs(user_id)

    gri = GoogleReaderImport(django_user.id)

    if wave == 0:
        gr_feed.loadItems(loadLimit=GR_LOAD_LIMIT)

    else:
        gr_feed.loadMoreItems(loadLimit=GR_LOAD_LIMIT)

    total_reads = gri.total_reads()
    date_limit  = max([gri.reg_date(), GR_OLDEST_DATE])
    total       = len(gr_feed.items)
    current     = 1

    continue_fetching = True

    for gr_article in gr_feed.items:

        if gri.reads() >= total_reads:
            gri.end(set_time=True)
            LOGGER.info(u'All read articles imported for user %s, stopping all '
                        u'tasks in turn.', django_user.username)
            return

        if gri.articles() >= GR_MAX_ARTICLES:
            gri.end(set_time=True)
            LOGGER.info(u'Maximum article limit reached for user %s, stopping '
                        u'import.', django_user.username)
            return

        if gr_article.time is None:
            LOGGER.warning(u'Article %s (feed “%s”, user %s) has no time. '
                           u'DATA=%s.', gr_article, gr_feed.title,
                           django_user.username, gr_article.time,
                           gr_article.data)

        else:
            if ftstamp(gr_article.time) < date_limit:
                continue_fetching = False
                break

        #LOGGER.info(u'Importing article “%s” from feed “%s” (%s/%s, wave %s)…',
        #            gr_article.title, gr_feed.title, current, total, wave + 1)

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

        current += 1
        gri.incr_articles()

        if gr_article.read:
            gri.incr_reads()

        if gr_article.starred:
            gri.incr_starred()

    # Remove the read items before loading more
    # else we leak much too much too muuuuuch…
    gr_feed.items[:GR_LOAD_LIMIT] = []
    # Avoid keeping strong references too…
    gr_feed.itemsById = {}
    # Having removed them here adds the benefit of
    # not storing them in the celery queue :-)

    if total == GR_LOAD_LIMIT:
        # Reaching the load limit means “Go for next wave”, because
        # there is probably more articles. We have to fetch to see.

        if gri.running():
                if wave < config.GR_WAVE_LIMIT:
                    if continue_fetching:
                        import_google_reader_articles.delay(
                            user_id, gr_feed, feed, wave=wave + 1)

                        LOGGER.info(u'Wave %s imported %s articles of '
                                    u'feed “%s” for user %s.', wave, total,
                                    gr_feed.title, django_user.username)

                    else:
                        LOGGER.warning(u'Datetime limit reached on feed “%s” '
                                       u'for user %s, stopping. %s article(s) '
                                       u'imported.', gr_feed.title,
                                       django_user.username, total)
                else:
                    LOGGER.warning(u'Wave limit reached on feed “%s”, for user '
                                   u'%s, stopping. %s article(s) imported.',
                                   gr_feed.title, django_user.username,
                                   total)
        else:
            LOGGER.warning(u'Forced import stop of feed “%s” for user %s, %s '
                           u'article(s) imported.', gr_feed.title,
                           django_user.username, total)
    else:
        # We have reached the "beginning" of the feed in GR.
        # Probably one with only a few subscribers, because
        # in normal conditions, GR data is kind of unlimited.
        LOGGER.info(u'Reached beginning of feed “%s” for user %s, %s '
                    u'article(s) imported.', gr_feed.title,
                    django_user.username, total)
