# -*- coding: utf-8 -*-

import logging
import datetime

from libgreader import GoogleReader, OAuth2Method

from celery import task

from django.conf import settings
from django.contrib.auth import get_user_model

from .models import RATINGS
from .models.nonrel import Article, Feed, Subscription, Read, User as MongoUser

#from ..base.utils import send_email_with_db_content

# Maximum number of articles fetched at each import wave.
GR_LOAD_LIMIT = 250

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

    import_google_reader_data.delay(user_id)


@task
def import_google_reader_data(user_id):

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

    LOGGER.info('Starting google reader import for user %s(%s)',
                user_infos['userEmail'], user_infos['userId'])

    mongo_user.gr_import_begin(user_infos)

    reader.buildSubscriptionList()

    total = len(reader.feeds)
    current = 1

    for gr_feed in reader.feeds:

        LOGGER.info(u'Importing feed “%s” (%s/%s)…',
                    gr_feed.title, current, total)

        Feed.objects(url=gr_feed.feedUrl,
                     site_url=gr_feed.siteUrl
                     ).update_one(set__url=gr_feed.feedUrl,
                                  set__site_url=gr_feed.siteUrl,
                                  set__name=gr_feed.title,
                                  upsert=True)

        feed = Feed.objects.get(url=gr_feed.feedUrl, site_url=gr_feed.siteUrl)
        tags = [c.label for c in gr_feed.getCategories()]

        Subscription.objects(feed=feed,
                             user=mongo_user,
                             tags=tags
                             ).update_one(set__feed=feed,
                                          set__user=mongo_user,
                                          set__tags=tags,
                                          upsert=True)

        import_google_reader_articles.delay(user_id, reader, gr_feed, feed)
        current += 1


@task
def import_google_reader_articles(user_id, reader, gr_feed, feed, wave=0):

    ftstamp = datetime.datetime.fromtimestamp

    django_user, mongo_user = get_user_from_dbs(user_id)

    if wave:
        gr_feed.loadMoreItems(loadLimit=GR_LOAD_LIMIT)

    else:
        gr_feed.loadItems(loadLimit=GR_LOAD_LIMIT)

    grand_total = len(gr_feed.items)
    total = grand_total - (wave * GR_LOAD_LIMIT)
    current = 1

    for gr_article in gr_feed.items[wave * GR_LOAD_LIMIT:]:

        LOGGER.debug(u'Importing article “%s” from feed “%s” (%s/%s, wave %s)…',
                     gr_article.title, gr_feed.title, current, total, wave + 1)

        Article.objects(title=gr_article.title,
                        url=gr_article.url).update_one(set__url=gr_article.url,
                                                       set__title=gr_article.title, # NOQA
                                                       set__feed=feed,
                                                       set__google_reader_original_data=gr_article.data, # NOQA
                                                       upsert=True)

        article = Article.objects.get(title=gr_article.title,
                                      url=gr_article.url)
        tags = [c.label for c in gr_feed.getCategories()]

        Read.objects(article=article,
                     user=mongo_user,
                     tags=tags
                     ).update_one(set__article=article,
                                  set__user=mongo_user,
                                  set__tags=tags,
                                  set__is_read=gr_article.read,
                                  set__date_created=ftstamp(gr_article.time),
                                  set__rating=article.default_rating +
                                  (RATINGS.STARRED if gr_article.starred
                                   else 0.0),
                                  upsert=True)

        current += 1

    if total % GR_LOAD_LIMIT == 0:
        # We got a multiple of the loadLimit. Go for next wave,
        # there could be more articles than that. We must fetch to see.
        import_google_reader_articles.delay(user_id, reader, gr_feed, feed,
                                            wave=wave + 1)

    else:
        LOGGER.info(u'Done importing %s article(s) in feed “%s”.',
                    grand_total, gr_feed.title)

        # This will save(), and end() the import if appropriate.
        if mongo_user.gr_import_update(grand_total):
            mongo_user.reload()
            LOGGER.info(u'Done importing Google Reader data (%s article(s), '
                        u'%s feed(s)).', mongo_user.gr_import.articles_imported,
                        mongo_user.gr_import.feeds_imported)

    # message: importing started
