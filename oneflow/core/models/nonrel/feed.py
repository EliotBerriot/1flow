# -*- coding: utf-8 -*-

import logging
import feedparser

from statsd import statsd
from celery import task
from constance import config

from mongoengine import Q, Document, NULLIFY, PULL
from mongoengine.fields import (IntField, StringField, URLField, BooleanField,
                                ListField, ReferenceField, DateTimeField)
from mongoengine.errors import ValidationError

from cache_utils.decorators import cached

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from ....base.utils import (RedisExpiringLock,
                            RedisSemaphore,
                            HttpResponseLogProcessor)

from ....base.fields import IntRedisDescriptor, DatetimeRedisDescriptor
from ....base.utils import ro_classproperty
from ....base.utils.dateutils import (now, timedelta, today, datetime,
                                      is_naive, make_aware, utc)

from .common import (DocumentHelperMixin,
                     CONTENT_NOT_PARSED,
                     ORIGIN_TYPE_FEEDPARSER,
                     ORIGIN_TYPE_WEBIMPORT,
                     USER_FEEDS_SITE_URL,
                     SPECIAL_FEEDS_DATA,
                     CACHE_ONE_WEEK)
from .tag import Tag
from .article import Article
from .user import User

LOGGER                = logging.getLogger(__name__)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT

__all__ = ('feed_update_latest_article_date_published',
           'feed_update_recent_articles_count',
           'feed_update_subscriptions_count',
           'feed_update_all_articles_count',
           'feed_refresh',
           'Feed',

           'feed_all_articles_count_default',
           'feed_good_articles_count_default',
           'feed_bad_articles_count_default',
           'feed_recent_articles_count_default',
           'feed_subscriptions_count_default', )


# ————————————— issue https://code.google.com/p/feedparser/issues/detail?id=404


import dateutil


def dateutilDateHandler(aDateString):
    return dateutil.parser.parse(aDateString).utctimetuple()

feedparser.registerDateHandler(dateutilDateHandler)


# ——————————————————————————————————————————————————————————————————— end issue


def feed_all_articles_count_default(feed, *args, **kwargs):

    return feed.articles.count()


def feed_good_articles_count_default(feed, *args, **kwargs):

    return feed.good_articles.count()


def feed_bad_articles_count_default(feed, *args, **kwargs):

    return feed.bad_articles.count()


def feed_recent_articles_count_default(feed, *args, **kwargs):

    return feed.recent_articles.count()


def feed_subscriptions_count_default(feed, *args, **kwargs):

    return feed.subscriptions.count()


@task(name='Feed.update_latest_article_date_published', queue='low')
def feed_update_latest_article_date_published(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_latest_article_date_published(*args, **kwargs)


@task(name='Feed.update_recent_articles_count', queue='low')
def feed_update_recent_articles_count(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_recent_articles_count(*args, **kwargs)


@task(name='Feed.update_subscriptions_count', queue='low')
def feed_update_subscriptions_count(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_subscriptions_count(*args, **kwargs)


@task(name='Feed.update_all_articles_count', queue='low')
def feed_update_all_articles_count(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.update_all_articles_count(*args, **kwargs)


@task(name='Feed.refresh', queue='medium')
def feed_refresh(feed_id, *args, **kwargs):

    feed = Feed.objects.get(id=feed_id)
    return feed.refresh(*args, **kwargs)


class Feed(Document, DocumentHelperMixin):
    name           = StringField(verbose_name=_(u'name'))
    url            = URLField(unique=True, verbose_name=_(u'url'))
    is_internal    = BooleanField(default=False)

    site_url       = URLField(verbose_name=_(u'web site'),
                              help_text=_(u'Website public URL, linked to the '
                                          u'globe icon in the source selector. '
                                          u'This is not the XML feed URL.'))
    slug           = StringField(verbose_name=_(u'slug'))
    tags           = ListField(ReferenceField('Tag', reverse_delete_rule=PULL),
                               default=list, verbose_name=_(u'tags'),
                               help_text=_(u'This tags are used only when '
                                           u'articles from this feed have no '
                                           u'tags already. They are assigned '
                                           u'to new subscriptions too.'))
    languages      = ListField(StringField(max_length=5,
                               choices=settings.LANGUAGES),
                               verbose_name=_(u'Languages'),
                               required=False,
                               help_text=_(u'Set this to more than one '
                                           u'language to help article '
                                           u'language detection if none '
                                           u'is set in articles.'))
    date_added     = DateTimeField(default=now, verbose_name=_(u'date added'))
    restricted     = BooleanField(default=False, verbose_name=_(u'restricted'),
                                  help_text=_(u'Is this feed available only to '
                                              u'paid subscribers on its '
                                              u'publisher\'s web site?'))
    closed         = BooleanField(default=False, verbose_name=_(u'closed'),
                                  help_text=_(u'Indicate that the feed is not '
                                              u'fetched anymore (see '
                                              u'“closed_reason” for why). '
                                              u'/!\\ WARNING: do not just '
                                              u'tick the checkbox; there is '
                                              u'a programmatic procedure to '
                                              u'close a feed properly.'))
    date_closed    = DateTimeField(verbose_name=_(u'date closed'))
    closed_reason  = StringField(verbose_name=_(u'closed reason'))

    fetch_interval = IntField(default=config.FEED_FETCH_DEFAULT_INTERVAL,
                              verbose_name=_(u'fetch interval'))
    last_fetch     = DateTimeField(verbose_name=_(u'last fetch'))

    # TODO: move this into WebSite to avoid too much parallel fetches
    # when using multiple feeds from the same origin website.
    fetch_limit_nr = IntField(default=config.FEED_FETCH_PARALLEL_LIMIT,
                              verbose_name=_(u'fetch limit'),
                              help_text=_(u'The maximum number of articles '
                                          u'that can be fetched from the feed '
                                          u'in parallel. If less than %s, '
                                          u'do not touch: the workers have '
                                          u'already tuned it from real-life '
                                          u'results.'))

    # Stored directly from feedparser data to avoid wasting BW.
    last_etag      = StringField(verbose_name=_(u'last etag'))
    last_modified  = StringField(verbose_name=_(u'modified'))

    mail_warned    = ListField(StringField())
    errors         = ListField(StringField())
    options        = ListField(IntField())
    duplicate_of   = ReferenceField(u'Feed', reverse_delete_rule=NULLIFY)
    notes          = StringField(verbose_name=_(u'Notes'),
                                 help_text=_(u'Internal notes for 1flow '
                                             u'staff related to this feed.'))

    good_for_use = BooleanField(verbose_name=_(u'Shown in selector'),
                                default=False,
                                help_text=_(u'Make this feed available to new '
                                            u'subscribers in the selector '
                                            u'wizard. Without this, the user '
                                            u'can still subscribe but he '
                                            u'must know it and manually enter '
                                            u'the feed address.'))
    thumbnail_url  = URLField(verbose_name=_(u'Thumbnail URL'),
                              help_text=_(u'Full URL of the thumbnail '
                                          u'displayed in the feed selector. '
                                          u'Can be hosted outside of 1flow.'))
    description_fr = StringField(verbose_name=_(u'Description (FR)'),
                                 help_text=_(u'Public description of the feed '
                                             u'in French language. '
                                             u'As Markdown.'))
    description_en = StringField(verbose_name=_(u'Description (EN)'),
                                 help_text=_(u'Public description of the feed '
                                             u'in English language. '
                                             u'As Markdown.'))

    meta = {
        'indexes': [
            'name',
            'site_url',
        ]
    }

    # ••••••••••••••••••••••••••••••• properties, cached descriptors & updaters

    # TODO: create an abstract class that will allow to not specify
    #       the attr_name here, but make it automatically created.
    #       This is an underlying implementation detail and doesn't
    #       belong here.
    latest_article_date_published = DatetimeRedisDescriptor(
        # 5 years ealier should suffice to get old posts when starting import.
        attr_name='f.la_dp', default=now() - timedelta(days=1826))

    all_articles_count = IntRedisDescriptor(
        attr_name='f.aa_c', default=feed_all_articles_count_default,
        set_default=True, min_value=0)

    good_articles_count = IntRedisDescriptor(
        attr_name='f.ga_c', default=feed_good_articles_count_default,
        set_default=True, min_value=0)

    bad_articles_count = IntRedisDescriptor(
        attr_name='f.ba_c', default=feed_bad_articles_count_default,
        set_default=True, min_value=0)

    recent_articles_count = IntRedisDescriptor(
        attr_name='f.ra_c', default=feed_recent_articles_count_default,
        set_default=True, min_value=0)

    subscriptions_count = IntRedisDescriptor(
        attr_name='f.s_c', default=feed_subscriptions_count_default,
        set_default=True, min_value=0)

    @ro_classproperty
    def good_feeds(cls):
        """ Return feeds suitable for use in the “add subscription”
            part of the source selector, eg feeds marked as usable by
            the administrators, not closed. """

        return cls.objects(restricted__ne=True).filter(
            # not internal, still open and validated by a human.
            (Q(is_internal__ne=True, closed__ne=True, good_for_use=True))

            # And not being duplicate of any other feed.
            & (Q(duplicate_of__exists=False) | Q(duplicate_of=None))

            # or just internal; internal feeds have no duplicate by nature,
            # and are not checked by humans.
            | Q(is_internal=True)).filter(
                )

    @property
    def latest_article(self):

        latest = self.get_articles(1)

        try:
            return latest[0]

        except:
            return None

    def update_latest_article_date_published(self):
        """ This seems simple, but this operations costs a lot in MongoDB. """

        try:
            # This query should still cost less than the pure and bare
            # `self.latest_article.date_published` which will first sort
            # all articles of the feed before getting the first of them.
            self.latest_article_date_published = self.recent_articles.order_by(
                '-date_published').first().date_published
        except:
            # Don't worry, the default value of
            # the descriptor should fill the gaps.
            pass

    @property
    def recent_articles(self):
        return self.good_articles.filter(
                date_published__gt=today()
                - timedelta(
                    days=config.FEED_ADMIN_MEANINGFUL_DELTA))

    def update_recent_articles_count(self, force=False):
        """ This task is protected to run only once per day,
            even if is called more. """

        urac_lock = RedisExpiringLock(self, lock_name='urac', expire_time=86100)

        if urac_lock.acquire() or force:
            self.recent_articles_count = self.recent_articles.count()

        elif not force:
            LOGGER.warning(u'No more than one update_recent_articles_count '
                           u'per day (feed %s).', self)
        #
        # Don't bother release the lock, this will
        # ensure we are not called until tomorrow.
        #

    def update_subscriptions_count(self):

        self.subscriptions_count = feed_subscriptions_count_default(self)

    # •••••••••••••••••••••••••••••••••••••••••••• end properties / descriptors

    # Doesn't seem to work, because Grappelli doesn't pick up Mongo classes.
    #
    # @staticmethod
    # def autocomplete_search_fields():
    #     return ('name__icontains', 'url__icontains', 'site_url__icontains', )

    def __unicode__(self):
        return _(u'{0} (#{1})').format(self.name, self.id)

    @property
    def refresh_lock(self):
        try:
            return self.__refresh_lock

        except AttributeError:
            self.__refresh_lock = RedisExpiringLock(self, lock_name='fetch')
            return self.__refresh_lock

    @property
    def fetch_limit(self):
        """ XXX: not used until correctly implemented.
            I removed the code calling this method on 20130910.
        """

        try:
            return self.__limit_semaphore

        except AttributeError:
            self.__limit_semaphore = RedisSemaphore(self, self.fetch_limit_nr)
            return self.__limit_semaphore

    def set_fetch_limit(self):
        """ XXX: not used until correctly implemented.
            I removed the code calling this method on 20130910.
        """

        new_limit = self.fetch_limit.set_limit()
        cur_limit = self.fetch_limit_nr

        if cur_limit != new_limit:
            self.fetch_limit_nr = new_limit
            self.save()

            LOGGER.info(u'Feed %s parallel fetch limit set to %s.',
                        self, new_limit)

    @classmethod
    def signal_pre_save_handler(cls, sender, document, **kwargs):

        feed = document

        for protocol in (u'http://', u'https://'):
            if feed.url.startswith(protocol + settings.SITE_DOMAIN):
                feed.is_internal = True
                break

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        feed = document

        if created:
            if feed._db_name != settings.MONGODB_NAME_ARCHIVE:
                # Update the feed immediately after creation.
                feed_refresh.delay(feed.id)

    def has_option(self, option):
        return option in self.options

    def reopen(self, commit=True):

        self.errors[:]     = []
        self.closed        = False
        self.date_closed   = now()
        self.closed_reason = u'Reopen on %s' % now().isoformat()
        self.save()

        LOGGER.info(u'Feed %s has just beed re-opened.', self)

    def close(self, reason=None, commit=True):
        self.update(set__closed=True, set__date_closed=now(),
                    set__closed_reason=reason or u'NO REASON GIVEN')

        LOGGER.info(u'Feed %s closed with reason "%s"!',
                    self, self.closed_reason)

        self.safe_reload()

    @property
    def articles(self):
        """ A simple version of :meth:`get_articles`. """

        return Article.objects(feeds__contains=self)

    @property
    def good_articles(self):
        """ Subscriptions should always use :attr:`good_articles` to give
            to users only useful content for them, whereas :class:`Feed`
            will use :attr:`articles` or :attr:`all_articles` to reflect
            real numbers.
        """

        #
        # NOTE: sync the conditions with @Article.is_good
        #       and invert them in @Feed.bad_articles
        #

        return self.articles(orphaned__ne=True, url_absolute=True).filter(
            Q(duplicate_of__exists=False) | Q(duplicate_of=None))

    @property
    def bad_articles(self):

        #
        # NOTE: invert these conditions in @Feed.good_articles
        #

        return self.articles(Q(orphaned=True) | Q(url_absolute=False)
                             | Q(duplicate_of__ne=None))

    def get_articles(self, limit=None):
        """ A parameter-able version of the :attr:`articles` property. """

        if limit:
            return self.articles.order_by('-date_published').limit(limit)

        return self.articles.order_by('-date_published')

    def validate(self, *args, **kwargs):
        try:
            super(Feed, self).validate(*args, **kwargs)

        except ValidationError as e:

            # We pop() because any error will close the feed, whatever it is.
            site_url_error = e.errors.pop('site_url', None)

            if site_url_error is not None:
                # Bad site URL, the feed is most probably totally unparsable.
                # Close it. Admins will be warned about it via mail from a
                # scheduled core task.
                #
                # WAS: if not 'bad_site_url' in self.mail_warned:
                #           self.mail_warned.append('bad_site_url')

                self.site_url = None
                self.close('Bad site url: %s' % str(site_url_error))

            # We pop() because any error will close the feed, whatever it is.
            url_error = e.errors.pop('url', None)

            if url_error is not None:
                if not self.closed:
                    self.close(str(url_error))

            thumbnail_url_error = e.errors.get('thumbnail_url', None)

            if thumbnail_url_error is not None:
                if self.thumbnail_url == u'':
                    # Just make this field not required. `required=False`
                    # in the Document definition is not sufficient.
                    e.errors.pop('thumbnail_url')

            if e.errors:
                raise ValidationError('ValidationError', errors=e.errors)

    def error(self, message, commit=True, last_fetch=False):
        """ Take note of an error. If the maximum number of errors is reached,
            close the feed and return ``True``; else just return ``False``.

            :param last_fetch: as a commodity, set this to ``True`` if you
                want this method to update the :attr:`last_fetch` attribute
                with the value of ``now()`` (UTC). Default: ``False``.

            :param commit: as in any other Django DB-related method, set
                this to ``False`` if you don't want this method to call
                ``self.save()``. Default: ``True``.
        """

        LOGGER.error(u'Error on feed %s: %s.', self, message)

        # Put the errors more recent first.
        self.errors.insert(0, u'%s @@%s' % (message, now().isoformat()))

        if last_fetch:
            self.last_fetch = now()

        retval = False

        if len(self.errors) >= config.FEED_FETCH_MAX_ERRORS:
            if not self.closed:
                self.close(u'Too many errors on the feed. Last was: %s'
                           % self.errors[0],

                           # prevent self.close() to reload()
                           # us before we save().
                           commit=False)

                LOGGER.critical(u'Too many errors on feed %s, closed.', self)

            # Keep only the most recent errors.
            self.errors = self.errors[:config.FEED_FETCH_MAX_ERRORS]

            retval = True

        if commit:
            self.save()

        return retval

    def create_article_from_url(self, url):

        # TODO: find article publication date while fetching content…
        # TODO: set Title during fetch…

        try:
            new_article, created = Article.create_article(
                url=url.replace(' ', '%20'),
                title=_(u'Imported item from {0}').format(url),
                feeds=[self], origin_type=ORIGIN_TYPE_WEBIMPORT)

        except:
            # NOTE: duplication handling is already
            # taken care of in Article.create_article().
            LOGGER.exception(u'Article creation from URL %s failed in '
                             u'feed %s.', url, self)
            return None, False

        mutualized = created is None

        if created or mutualized:
            self.recent_articles_count += 1
            self.all_articles_count += 1

        self.latest_article_date_published = now()

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        for subscription in self.subscriptions:
            subscription.create_read(new_article, verbose=created)

        # Don't forget the parenthesis else we return ``False`` everytime.
        return new_article, created or (None if mutualized else False)

    def create_article_from_feedparser(self, article, feed_tags):
        """ Take a feedparser item and a list of Feed subscribers and
            feed tags, and create the corresponding Article and Read(s). """

        feedparser_content = getattr(article, 'content', CONTENT_NOT_PARSED)

        if isinstance(feedparser_content, list):
            feedparser_content = feedparser_content[0]
            content = feedparser_content.get('value', CONTENT_NOT_PARSED)

        else:
            content = feedparser_content

        try:
            date_published = datetime(*article.published_parsed[:6])

        except:
            date_published = None

        else:
            # This is probably a false assumption, but have currently no
            # simple way to get the timezone of the feed. Anyway, we *need*
            # an offset aware for later comparisons. BTW, in most cases,
            # feedparser already did a good job before reaching here.
            if is_naive(date_published):
                date_published = make_aware(date_published, utc)

        tags = list(Tag.get_tags_set((
                    t['term'] for t in article.get('tags', [])
                    # Sometimes, t['term'] can be None.
                    # http://dev.1flow.net/webapps/1flow/group/4082/
                    if t['term'] is not None), origin=self) | set(feed_tags))

        try:
            new_article, created = Article.create_article(
                # Sometimes feedparser gives us URLs with spaces in them.
                # Using the full `urlquote()` on an already url-quoted URL
                # could be very destructive, thus we patch only this case.
                #
                # If there is no `.link`, we get '' to be able to `replace()`,
                # but in fine `None` is a more regular "no value" mean. Sorry
                # for the weird '' or None that just does the job.
                url=getattr(article, 'link', '').replace(' ', '%20') or None,

                # We *NEED* a title, but as we have no article.lang yet,
                # it must be language independant as much as possible.
                title=getattr(article, 'title', u' '),

                excerpt=content, date_published=date_published,
                feeds=[self], tags=tags, origin_type=ORIGIN_TYPE_FEEDPARSER)

        except:
            # NOTE: duplication handling is already
            # taken care of in Article.create_article().
            LOGGER.exception(u'Article creation failed in feed %s.', self)
            return False

        if created:
            new_article.add_original_data('feedparser', unicode(article))

        mutualized = created is None

        if created or mutualized:
            self.recent_articles_count += 1
            self.all_articles_count += 1

        # Update the "latest date" kind-of-cache.
        if date_published is not None and \
                date_published > self.latest_article_date_published:
            self.latest_article_date_published = date_published

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        for subscription in self.subscriptions:
            subscription.create_read(new_article, verbose=created)

        # Don't forget the parenthesis else we return ``False`` everytime.
        return created or (None if mutualized else False)

    def build_refresh_kwargs(self):

        kwargs = {}

        # Implement last-modified & etag headers to save BW.
        # Cf. http://pythonhosted.org/feedparser/http-etag.html
        if self.last_modified:
            kwargs['modified'] = self.last_modified

        else:
            kwargs['modified'] = self.latest_article_date_published

        if self.last_etag:
            kwargs['etag'] = self.last_etag

        # Circumvent https://code.google.com/p/feedparser/issues/detail?id=390
        http_logger        = HttpResponseLogProcessor()
        kwargs['referrer'] = self.site_url
        kwargs['handlers'] = [http_logger]

        return kwargs, http_logger

    def refresh_must_abort(self, force=False, commit=True):
        """ Returns ``True`` if one or more abort conditions is met.
            Checks the feed cache lock, the ``last_fetch`` date, etc.
        """

        if self.closed:
            LOGGER.info(u'Feed %s is closed. refresh aborted.', self)
            return True

        if self.is_internal:
            LOGGER.info(u'Feed %s is internal, no need to refresh.', self)
            return True

        if config.FEED_FETCH_DISABLED:
            # we do not raise .retry() because the global refresh
            # task will call us again anyway at next global check.
            LOGGER.info(u'Feed %s refresh disabled by configuration.', self)
            return True

        if not self.refresh_lock.acquire():
            if force:
                LOGGER.warning(u'Forcing refresh for feed %s, despite of '
                               u'lock already acquired.', self)
                self.refresh_lock.release()
                self.refresh_lock.acquire()
            else:
                LOGGER.info(u'Refresh for %s already running, aborting.', self)
                return True

        if self.last_fetch is not None and self.last_fetch >= (
                now() - timedelta(seconds=self.fetch_interval)):
            if force:
                LOGGER.warning(u'Forcing refresh of recently fetched feed %s.',
                               self)
            else:
                LOGGER.info(u'Last refresh of feed %s too recent, aborting.',
                            self)
                return True

        return False

    def has_feedparser_error(self, parsed_feed):

        if parsed_feed.get('bozo', None) is None:
            return False

        error = parsed_feed.get('bozo_exception', None)

        # Charset declaration problems are harmless (until they are not).
        if str(error).startswith('document declared as'):
            LOGGER.warning('Feed %s: %s', self, error)
            return False

        # currently, I've encountered no error fatal to feedparser.
        return False

        # Thus, no need for this yet, but it's ready.
        #self.error(u'feedparser error %s', str(error))

        # Do not close for this: it can be a temporary error.
        # if isinstance(exception, SAXParseException):
        #     self.close(reason=str(exception))
        #     return True
        #
        #return False
        #
        pass

    @staticmethod
    def throttle_fetch_interval(interval, news, mutualized,
                                duplicates, etag, modified):
        """ Try to adapt dynamically the fetch interval, to fetch more feeds
            that produce a lot of new entries, and less the ones that do not.

            Feeds which correctly implement etags/last_modified should not
            be affected negatively.

            Feeds producing a lot of news should see their interval lower
            quickly. Feeds producing only duplicates will be fetched less.
            Feeds producing mutualized will still be fetched fast, because
            they are producing new content, even if it mutualized with other
            feeds.

            Feeds producing nothing and that do not implement etags/modified
            should suffer a lot and burn in hell like sheeps.

            This is a static method to allow better testing from outside the
            class.
        """

        if news:
            if mutualized:
                if duplicates:
                    multiplicator = 0.8

                else:
                    multiplicator = 0.7

            elif duplicates:
                multiplicator = 0.9

            else:
                # Only fresh news. My Gosh, this feed
                # produces a lot! Speed up fetches!!
                multiplicator = 0.6

            if mutualized > min(5, config.FEED_FETCH_RAISE_THRESHOLD):
                # The thing is prolific. Speed up even more.
                multiplicator *= 0.9

            if news > min(5, config.FEED_FETCH_RAISE_THRESHOLD):
                # The thing is prolific. Speed up even more.
                multiplicator *= 0.9

        elif mutualized:
            # Speed up, also. But as everything was already fetched
            # by komrades, no need to speed up too much. Keep cool.

            if duplicates:
                multiplicator = 0.9

            else:
                multiplicator = 0.8

        elif duplicates:
            # If there are duplicates, either the feed doesn't use
            # etag/last_mod [correctly], either its a master/subfeed
            # for which articles have already been fetched by a peer.

            if etag or modified:
                # There is something wrong with the website,
                # it should not have offered us anything when
                # using etag/last_modified.
                multiplicator = 1.25

            else:
                multiplicator = 1.125

        else:
            # No duplicates (feed probably uses etag/last_mod) but no
            # new articles, nor mutualized. Keep up the good work, don't
            # change anything.
            multiplicator = 1.0

        interval *= multiplicator

        if interval > min(604800, config.FEED_FETCH_MAX_INTERVAL):
            interval = config.FEED_FETCH_MAX_INTERVAL

        if interval < max(60, config.FEED_FETCH_MIN_INTERVAL):
            interval = config.FEED_FETCH_MIN_INTERVAL

        return interval

    def refresh(self, force=False):
        """ Find new articles in an RSS feed.

            .. note:: we don't release the lock, this is intentional. The
                next refresh should not occur within the feed official
                refresh interval, this would waste resources.
        """

        # In tasks, doing this is often useful, if
        # the task waited a long time before running.
        self.safe_reload()

        if self.refresh_must_abort(force=force):
            self.refresh_lock.release()
            return

        LOGGER.info(u'Refreshing feed %s…', self)

        feedparser_kwargs, http_logger = self.build_refresh_kwargs()
        parsed_feed = feedparser.parse(self.url, **feedparser_kwargs)

        # In case of a redirection, just check the last hop HTTP status.
        try:
            feed_status = http_logger.log[-1]['status']

        except IndexError, e:
            # The website could not be reached? Network
            # unavailable? on my production server???

            # self.refresh_lock.release() ???
            raise feed_refresh.retry((self.id, ), exc=e)

        # Stop on HTTP errors before stopping on feedparser errors,
        # because he is much more lenient in many conditions.
        if feed_status in (400, 401, 402, 403, 404, 500, 502, 503):
            self.error(u'HTTP %s on %s' % (http_logger.log[-1]['status'],
                       http_logger.log[-1]['url']), last_fetch=True)
            return

        if self.has_feedparser_error(parsed_feed):
            # the method will have already call self.error().
            return

        if feed_status == 304:
            LOGGER.info(u'No new content in feed %s.', self)

            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.fetch.global.unchanged')

        else:
            tags = Tag.get_tags_set(getattr(parsed_feed, 'tags', []),
                                    origin=self)

            if tags != set(self.tags):
                # We consider the publisher knows the nature of his content
                # better than us, and we trust him about the tags he sets
                # on the feed. Thus, we don't union() with the new tags,
                # but simply replace current by new ones.
                LOGGER.info(u'Updating tags of feed %s from %s to %s.',
                            self.tags, tags)
                self.tags = list(tags)

            new_articles  = 0
            duplicates    = 0
            mutualized    = 0

            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.fetch.global.updated')

            for article in parsed_feed.entries:
                created = self.create_article_from_feedparser(article, tags)

                if created:
                    new_articles += 1

                elif created is False:
                    duplicates += 1

                else:
                    mutualized += 1

            # Store the date/etag for next cycle. Doing it after the full
            # refresh worked ensures that in case of any exception during
            # the loop, the retried refresh will restart on the same
            # entries without loosing anything.
            self.last_modified = getattr(parsed_feed, 'modified', None)
            self.last_etag     = getattr(parsed_feed, 'etag', None)

            if not force:
                # forcing the refresh is most often triggered by admins
                # and developers. It should not trigger the adaptative
                # throttling computations, because it generates a lot
                # of false-positive duplicates, and will.

                new_interval = Feed.throttle_fetch_interval(self.fetch_interval,
                                                            new_articles,
                                                            mutualized,
                                                            duplicates,
                                                            self.last_etag,
                                                            self.last_modified)

                if new_interval != self.fetch_interval:
                    LOGGER.info(u'Fetch interval changed from %s to %s '
                                u'for feed %s (%s new article(s), %s '
                                u'duplicate(s)).', self.fetch_interval,
                                new_interval, self, new_articles, duplicates)

                    self.fetch_interval = new_interval

            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.global.fetched', new_articles)
                spipe.incr('feeds.refresh.global.duplicates', duplicates)
                spipe.incr('feeds.refresh.global.mutualized', mutualized)

        # Everything went fine, be sure to reset the "error counter".
        self.errors[:]  = []
        self.last_fetch = now()
        self.save()

        with statsd.pipeline() as spipe:
            spipe.incr('feeds.refresh.fetch.global.done')

        # As the last_fetch is now up-to-date, we can release the fetch lock.
        # If any other refresh job comes, it will check last_fetch and will
        # terminate if called too early.
        self.refresh_lock.release()


# ——————————————————————————————————————————————————————— external delete rules
#                                            Defined here to avoid import loops


Feed.register_delete_rule(Article, 'feeds', PULL)


# ———————————————————————————————————————— external non-subscription properties
#                                            Defined here to avoid import loops


def User_web_import_feed_property_get(self):

    return get_or_create_special_feed(self, *SPECIAL_FEEDS_DATA['web_import'])


def User_sent_items_feed_property_get(self):

    return get_or_create_special_feed(self, *SPECIAL_FEEDS_DATA['sent_items'])


def User_received_items_feed_property_get(self):

    return get_or_create_special_feed(self,
                                      *SPECIAL_FEEDS_DATA['received_items'])


@cached(CACHE_ONE_WEEK)
def get_or_create_special_feed(user, url_template, default_name):

    try:
        return Feed.objects.get(url=url_template.format(user=user))

    except Feed.DoesNotExist:

        #
        # NOTE: using the username in the feed name will allow other
        # users to easily subscribe to each other's import feeds, and
        # distinguish them if they have many.
        #

        return Feed(url=url_template.format(user=user),
                    name=default_name.format(
                        user.username or (u'#%s' % user.id)),

                    # TODO: make this dynamic, given the
                    # free/premium level of users ?
                    restricted=True,

                    # By default, these feeds are internal,
                    # not part of the add-subsription form.
                    is_internal=True,

                    site_url=USER_FEEDS_SITE_URL.format(user=user)).save()

        # This will be done in the subscription property. DRY.
        #Subscription.subscribe_user_to_feed(user, feed)


User.web_import_feed     = property(User_web_import_feed_property_get)
User.sent_items_feed     = property(User_sent_items_feed_property_get)
User.received_items_feed = property(User_received_items_feed_property_get)
