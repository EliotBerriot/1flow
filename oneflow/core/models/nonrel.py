# -*- coding: utf-8 -*-

import logging
import datetime
import dateutil
import requests
import strainer
import html2text
import feedparser

from random import randrange
from constance import config

from celery.contrib.methods import task as celery_task_method
from celery.exceptions import SoftTimeLimitExceeded

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, ValidationError
from mongoengine.errors import NotUniqueError
from mongoengine.fields import (IntField, FloatField, BooleanField,
                                DateTimeField,
                                ListField, StringField,
                                URLField,
                                ReferenceField, GenericReferenceField,
                                EmbeddedDocumentField)

from django.core.mail import mail_admins
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from ...base.utils import (connect_mongoengine_signals,
                           detect_encoding_from_requests_response,
                           SimpleCacheLock, AlreadyLockedException,
                           HttpResponseLogProcessor, RedisStatsCounter)
from .keyval import FeedbackDocument

LOGGER = logging.getLogger(__name__)

feedparser.USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' # NOQA

# Don't use any lang-dependant values (eg. _(u'NO CONTENT'))
CONTENT_NOT_PARSED    = None
CONTENT_TYPE_NONE     = 0
CONTENT_TYPE_HTML     = 1
CONTENT_TYPE_MARKDOWN = 2
CONTENT_TYPE_IMAGE    = 100
CONTENT_TYPE_VIDEO    = 200
CONTENT_TYPES_FINAL   = (CONTENT_TYPE_MARKDOWN,
                         CONTENT_TYPE_IMAGE, CONTENT_TYPE_VIDEO,
                         )

CONTENT_PREPARSING_NEEDS_GHOST = 1
CONTENT_FETCH_LIKELY_MULTIPAGE = 2

# MORE CONTENT_PREPARSING_NEEDS_* TO COME

# These classes will be re-used inside every worker; we instanciate only once.
STRAINER_EXTRACTOR = strainer.Strainer(parser='lxml', add_score=True)

if config.FEED_FETCH_GHOST_ENABLED:
    try:
        import ghost
    except:
        ghost = None # NOQA
    else:
        GHOST_BROWSER = ghost.Ghost()


else:
    ghost = None # NOQA


now       = datetime.datetime.now
#today     = datetime.date.today
timedelta = datetime.timedelta


# ••••••••••••• issue https://code.google.com/p/feedparser/issues/detail?id=404

def dateutilDateHandler(aDateString):
    return dateutil.parser.parse(aDateString).utctimetuple()

feedparser.registerDateHandler(dateutilDateHandler)

# ••••••••• end issue •••••••••••••••••••••••••••••••••••••••••••••••••••••••••


class FeedStatsCounter(RedisStatsCounter):
    """ This counter represents a given feed's statistics.

        It will increment global feeds statistics too, so that we
        developpers don't have to worry about 2 types of statistics
        counters in the Feed methods / tasks.
    """

    key_base = 'feeds'

    def incr_fetched(self):
        if self.key_base != global_feed_stats.key_base:
            global_feed_stats.incr_fetched()

        return self.fetched(increment=True)

    def fetched(self, increment=False):

        if self.key_base != global_feed_stats.key_base:
            # in case we want to reset.
            global_feed_stats.fetched(increment)

        return RedisStatsCounter._int_incr_key(
            self.key_base + ':fetch', increment)

    def incr_dupes(self):
        if self.key_base != global_feed_stats.key_base:
            global_feed_stats.incr_dupes()

        return self.dupes(increment=True)

    def dupes(self, increment=False):

        if self.key_base != global_feed_stats.key_base:
            # in case we want to reset.
            global_feed_stats.dupes(increment)

        return RedisStatsCounter._int_incr_key(
            self.key_base + ':dupes', increment)

# This one will keep track of all counters, globally, for all feeds.
global_feed_stats = FeedStatsCounter()

# Until we patch Ghost to use more than one Xvfb at the same time,
# we are tied to ensure there is only one running at a time.
global_ghost_lock = SimpleCacheLock('__ghost.py__')


class Source(Document):
    """ The "original source" for similar articles: they have different authors,
        different contents, but all refer to the same information, which can
        come from the same article on the net (or radio, etc).

        Eg:
            - article1 on Le Figaro
            - article2 on Liberation
            - both refer to the same AFP news, but have different content.

    """
    type    = StringField()
    uri     = URLField(unique=True)
    name    = StringField()
    authors = ListField(ReferenceField('User'))
    slug    = StringField()


class Feed(Document):
    # TODO: init
    name           = StringField(verbose_name=_(u'name'))
    url            = URLField(unique=True, verbose_name=_(u'url'))
    site_url       = URLField(verbose_name=_(u'web site'))
    slug           = StringField(verbose_name=_(u'slug'))
    restricted     = BooleanField(default=False, verbose_name=_(u'restricted'))
    closed         = BooleanField(default=False, verbose_name=_(u'closed'))
    date_added     = DateTimeField(default=now, verbose_name=_(u'added'))

    fetch_interval = IntField(default=config.FEED_FETCH_DEFAULT_INTERVAL,
                              verbose_name=_(u'fetch interval'))
    last_fetch     = DateTimeField(verbose_name=_(u'last fetch'))

    # Stored directly from feedparser data to avoid wasting BW.
    last_etag      = StringField(verbose_name=_(u'last etag'))
    last_modified  = StringField(verbose_name=_(u'modified'))

    mail_warned    = ListField(StringField())

    options        = ListField(IntField())

    def __unicode__(self):
        return _(u'%s (#%s) from %s') % (self.name, self.id, self.url)

    @classmethod
    def signal_post_save_handler(cls, sender, document, **kwargs):

        # Update the feed with current content.
        document.refresh.delay()

    def has_option(self, option):
        return option in self.options

    def get_articles(self, limit=None):

        if limit:
            return Article.objects.filter(
                feed=self).order_by('-date_published').limit(limit)

        return Article.objects.filter(
            feed=self).order_by('-date_published')

    def validate(self, *args, **kwargs):
        try:
            super(Feed, self).validate(*args, **kwargs)

        except ValidationError as e:

            # Ignore/wrap errors about these fields:
            if e.errors.pop('site_url', None) is not None:
                if not 'bad_site_url' in self.mail_warned:
                    mail_admins('Feed {0} has a bad `site_url`'.format(self),
                                (u"\n\n It is currently set to “ {0} ”.\n\n"
                                u"You should fix it.\n\n").format(
                                self.site_url))
                    self.mail_warned.append('bad_site_url')

            if e.errors:
                raise ValidationError('ValidationError', errors=e.errors)

    def get_latest_article(self):

        latest = self.get_articles(1)

        try:
            return latest[0]

        except:
            return None

    def get_subscribers(self):
        return [
            s.user
            for s in Subscription.objects.filter(feed=self)
        ]

    def create_article_and_reads(self, article, subscribers, tags):
        """ Take a feedparser item and lists of Feed subscribers and
            tags, then create the corresponding Article and Read(s). """

        feedparser_content = getattr(article, 'content', CONTENT_NOT_PARSED)

        if isinstance(feedparser_content, list):
            feedparser_content = feedparser_content[0]
            content = feedparser_content.get('value', CONTENT_NOT_PARSED)

        else:
            content = feedparser_content

        try:
            date_published = datetime.datetime(
                *article.published_parsed[:6])
        except:
            date_published = None

        new_article, created = Article.create_article(
            url=article.link,
            title=article.title,
            content=content,
            date_published=date_published,
            feed=self,

            # Convert to unicode before saving,
            # else the article won't validate.
            feedparser_original_data=unicode(article))

        # If the article was not created, reads creation are likely
        # to fail too. Don't display warnings, they are quite boring.
        new_article.create_reads(subscribers, tags, verbose=created)

        return created

    def check_refresher(self):

        if self.closed:
            LOGGER.error(u'Feed %s is closed. refresh aborted.', self)
            return

        if config.FEED_FETCH_DISABLED:
            # we do not raise .retry() because the global refresh
            # task will call us again anyway at next global check.
            LOGGER.warning(u'Feed %s refresh disabled by configuration.', self)
            return

        my_lock = SimpleCacheLock(self)

        if my_lock.acquire():
            # no refresher is running.
            # Release the lock and launch one.
            my_lock.release()

            if config.FEED_REFRESH_RANDOMIZE:
                self.refresh.apply_async(
                    (), countdown=randrange((self.fetch_interval or
                                            config.FEED_FETCH_DEFAULT_INTERVAL)
                                            - 15))

            else:
                self.refresh.delay()

    def build_refresh_kwargs(self):

        kwargs = {}

        # Implement last-modified & etag headers to save BW.
        # Cf. http://pythonhosted.org/feedparser/http-etag.html
        if self.last_modified:
            kwargs['modified'] = self.last_modified

        else:
            latest_article = self.get_latest_article()

            if latest_article:
                latest_date = latest_article.date_published

                if latest_date:
                    kwargs['modified'] = latest_date

        if self.last_etag:
            kwargs['etag'] = self.last_etag

        # Circumvent https://code.google.com/p/feedparser/issues/detail?id=390
        http_logger        = HttpResponseLogProcessor()
        kwargs['referrer'] = self.site_url
        kwargs['handlers'] = [http_logger]

        return kwargs, http_logger

    def refresh_must_abort(self, force=False):
        """ Returns ``True`` if one or more abort conditions is met.
            Checks the feed cache lock, the ``last_fetch`` date, etc.
        """

        if self.closed:
            LOGGER.error(u'Feed %s is closed. refresh aborted.', self)
            return True

        if config.FEED_FETCH_DISABLED:
            # we do not raise .retry() because the global refresh
            # task will call us again anyway at next global check.
            LOGGER.warning(u'Feed %s refresh disabled by configuration.', self)
            return

        my_lock = SimpleCacheLock(self)

        if not my_lock.acquire():
            if force:
                LOGGER.warning(u'Forcing reschedule of fetcher for feed %s.',
                               self)
                my_lock.release()
                my_lock.acquire()
            else:
                LOGGER.info(u'Refresh for %s already scheduled, aborting.',
                            self)
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

    @celery_task_method(name='Feed.refresh', queue='low')  # rate_limit='10/s')
    def refresh(self, force=False):
        """ Find new articles in an RSS feed.

            .. note:: we don't release the lock, this is intentional. The
                next refresh should not occur within the feed official
                refresh interval, this would waste resources.
        """

        if self.refresh_must_abort(force=force):
            return

        # Launch the next fetcher right now, in order for the duration
        # of the current fetch not to delay the next and make the actual
        # fetch interval be longer than advertised.
        self.refresh.apply_async((), countdown=self.fetch_interval
                                 or config.FEED_FETCH_DEFAULT_INTERVAL)

        LOGGER.info(u'Refreshing feed %s…', self)

        feedparser_kwargs, http_logger = self.build_refresh_kwargs()
        parsed_feed = feedparser.parse(self.url, **feedparser_kwargs)

        # In case of a redirection, just check the last hop HTTP status.
        try:
            feed_status = http_logger.log[-1]['status']

        except IndexError, e:
            # The website could not be reached?

            # NOT until https://github.com/celery/celery/issues/1458 is fixed. # NOQA
            #raise self.refresh.retry(exc=e)

            # NOTE: the feed refresh will be launched
            # again by the global scheduled class.
            LOGGER.exception(u'Refresh feed %s status failed.', self)
            return e

        if feed_status != 304:

            fetch_counter = FeedStatsCounter(self)
            subscribers   = self.get_subscribers()
            tags          = getattr(parsed_feed, 'tags', [])

            try:
                for article in parsed_feed.entries:
                    if self.create_article_and_reads(article,
                                                     subscribers, tags):
                        fetch_counter.incr_fetched()
                    else:
                        fetch_counter.incr_dupes()

            except Exception, e:
                # NOT until https://github.com/celery/celery/issues/1458 is fixed. # NOQA
                #raise self.refresh.retry(exc=e)

                # NOTE: the feed refresh will be launched
                # again by the global scheduled class.
                LOGGER.exception(u'Refresh feed %s failed.', self)
                return e

            # Store the date/etag for next cycle. Doing it after the full
            # refresh worked ensures that in case of any exception during
            # the loop, the retried refresh will restart on the same
            # entries without loosing anything.
            self.last_modified = getattr(parsed_feed, 'modified', None)
            self.last_etag     = getattr(parsed_feed, 'etag', None)

        else:
            LOGGER.info(u'No new content in feed %s.', self)

        # Avoid running too near refreshes. Even if the feed didn't include
        # new items, we will not check it again until fetch_interval is spent.
        self.last_fetch = now()
        self.save()


class Subscription(Document):
    feed = ReferenceField('Feed')
    user = ReferenceField('User', unique_with='feed')

    # allow the user to rename the field in its own subscription
    name = StringField()

    # these are kind of 'folders', but can be more dynamic.
    tags = ListField(StringField())


class Group(Document):
    name = StringField(unique_with='creator')
    creator = ReferenceField('User')
    administrators = ListField(ReferenceField('User'))
    members = ListField(ReferenceField('User'))
    guests = ListField(ReferenceField('User'))


class Article(Document):
    title      = StringField(max_length=256, required=True,
                             verbose_name=_(u'Title'))
    slug       = StringField(max_length=256)
    url        = URLField(unique=True, verbose_name=_(u'Public URL'))
    pages_urls = ListField(URLField(), verbose_name=_(u'Next pages URLs'),
                           help_text=_(u'In case of a multi-pages article, '
                                       u'other pages URLs will be here.'))
    # not yet.
    #short_url  = URLField(unique=True, verbose_name=_(u'1flow URL'))

    word_count = IntField(verbose_name=_(u'Word count'))

    authors    = ListField(ReferenceField('User'))
    publishers = ListField(ReferenceField('User'))

    date_published = DateTimeField(verbose_name=_(u'date published'),
                                   help_text=_(u"When the article first "
                                               u"appeared on the publisher's "
                                               u"website."))
    date_added     = DateTimeField(default=now,
                                   verbose_name=_(u'Date added'),
                                   help_text=_(u'When the article was added '
                                               u'to the 1flow database.'))

    default_rating = FloatField(default=0.0, verbose_name=_(u'default rating'),
                                help_text=_(u'Rating used as a base when a '
                                            u'user has not already rated the '
                                            u'content.'))
    language       = StringField(verbose_name=_(u'Article language'))
    text_direction = StringField(verbose_name=_(u'Text direction'))
    comments       = ListField(ReferenceField('Comment'))

    abstract      = StringField(verbose_name=_(u'abstract'),
                                help_text=_(u'Small exerpt of content, '
                                            u'if applicable'))
    content       = StringField(default=CONTENT_NOT_PARSED,
                                verbose_name=_(u'Content'),
                                help_text=_(u'Article content'))
    content_type  = IntField(default=CONTENT_TYPE_NONE,
                             verbose_name=_(u'Content type'),
                             help_text=_(u'Type of article content '
                                         u'(text, image…)'))
    content_error = StringField(verbose_name=_(u'Error'),
                                help_text=_(u'Error when fetching content'))

    # This should go away soon, after a full re-parsing.
    google_reader_original_data = StringField()
    feedparser_original_data    = StringField()

    # A snap / a serie of snaps references the original article.
    # An article references its source (origin blog / newspaper…)
    source = GenericReferenceField()

    # The feed from which we got this article from. Can be ``None`` if the
    # user snapped an article directly from a standalone web page in browser.
    feed = ReferenceField('Feed')

    # Avoid displaying duplicates to the user.
    duplicates = ListField(ReferenceField('Article'))

    def __unicode__(self):
        return _(u'%s (#%s) from %s') % (self.title, self.id, self.url)

    def validate(self, *args, **kwargs):
        try:
            super(Article, self).validate(*args, **kwargs)

        except ValidationError as e:
            # Ignore errors about these fields:
            e.errors.pop('google_reader_original_data', None)
            e.errors.pop('feedparser_original_data', None)

            if e.errors:
                raise ValidationError('ValidationError', errors=e.errors)

    def is_origin(self):
        return isinstance(self.source, Source)

    def create_reads(self, users, tags, verbose=True):

        for user in users:
            new_read = Read(article=self,
                            user=user,
                            tags=tags)
            try:
                new_read.save()

            except (NotUniqueError, DuplicateKeyError):
                if verbose:
                    LOGGER.warning(u'Duplicate read %s!', new_read)

            except:
                LOGGER.exception(u'Could not save read %s!', new_read)

    @classmethod
    def create_article(cls, title, url, feed, **kwargs):

        new_article = cls(title=title, url=url, feed=feed)

        try:
            new_article.save()

        except (DuplicateKeyError, NotUniqueError):
            LOGGER.warning(u'Duplicate article “%s” (url: %s) from feed “%s”!',
                           title, url, feed.name)

            return cls.objects.get(url=url), False

        else:
            if kwargs:
                for key, value in kwargs.items():
                    setattr(new_article, key, value)

                new_article.save()

            LOGGER.info(u'Created article %s in feed %s.', new_article, feed)

            return new_article, True

    @celery_task_method(name='Article.fetch_content', queue='medium',
                        default_retry_delay=3600, soft_time_limit=50)
    def fetch_content(self, force=False, commit=True):

        if self.content_type in CONTENT_TYPES_FINAL and not force:
            LOGGER.warning(u'Article %s has already been fetched.', self)
            return

        if self.content_error:
            if force:
                self.content_error = None
                if commit:
                    self.save()
            else:
                LOGGER.warning(u'Article %s has a fetching error, aborting '
                               u'(%s).', self, self.content_error)
                return

        if config.ARTICLE_FETCHING_DISABLED:
            LOGGER.warning(u'Article fetching disabled in configuration.')
            return

        #
        # TODO: implement switch based on content type.
        #

        # Testing for https://github.com/celery/celery/issues/1459
        #
        # from celery import current_task
        #
        # LOGGER.warning('>>> %s %s RAISING!', self, current_task.__self__)
        # e = RuntimeError('TESTING_CURRENT_TASK')
        # self.content_error = str(e)
        # self.save()
        #
        # raise self.fetch_content.retry(exc=e, countdown=randrange(60))

        try:
            self.fetch_content_text(force=force, commit=commit)

        except AlreadyLockedException, e:
            # This won't work because of issue 1458, we have to fake.
            #raise self.fetch_content.retry(exc=e, countdown=randrange(60))

            self.fetch_content.apply_async((), countdown=randrange(60))
            return

        except SoftTimeLimitExceeded, e:
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'Extraction took too long for article %s.', self)
            raise

        except Exception, e:
            # TODO: except urllib2.error: retry with longer delay.
            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Extraction failed for article %s.', self)
            raise

    def fetch_content_image(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_IMAGE_DISABLED:
            LOGGER.warning(u'Article video fetching disabled in configuration.')
            return

    def fetch_content_video(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_VIDEO_DISABLED:
            LOGGER.warning(u'Article video fetching disabled in configuration.')
            return

    def needs_ghost_preparser(self):

        return config.FEED_FETCH_GHOST_ENABLED and \
            self.feed.has_option(CONTENT_PREPARSING_NEEDS_GHOST)

    def likely_multipage_content(self):

        return self.feed.has_option(CONTENT_FETCH_LIKELY_MULTIPAGE)

    def get_next_page_link(self, from_content):
        """ Try to find a “next page” link in the partial content given as
            parameter. """

        #soup = BeautifulSoup(from_content)

        return None

    def prepare_content_text(self, url=None):
        """ :param:`url` should be set in the case of multipage content. """

        fetch_url = url or self.url

        if self.needs_ghost_preparser():

            if ghost is None:
                LOGGER.warning(u'Ghost module is not available, content of '
                               u'article %s will be incomplete.', self)
                return requests.get(fetch_url).content

                # The lock will raise an exception if it is already acquired.
                with global_ghost_lock:
                    GHOST_BROWSER.open(fetch_url)
                    page, resources = GHOST_BROWSER.wait_for_page_loaded()

                    #
                    # TODO: detect encoding!!
                    #
                    return page

        response = requests.get(fetch_url)
        encoding = detect_encoding_from_requests_response(response)

        return response.content, encoding

    def fetch_content_text_one_page(self, url=None):
        """ Internal function. Please do not call.
            Use :meth:`fetch_content_text` instead. """

        content, encoding = self.prepare_content_text(url=url)

        if not encoding:
            LOGGER.warning(u'Could not properly detect encoding for '
                           u'article %s, using utf-8 as fallback.', self)
            encoding = 'utf-8'

        if config.ARTICLE_FETCHING_DEBUG:
            try:
                LOGGER.info(u'————————— #%s HTML %s > %s —————————'
                            u'\n%s\n'
                            u'————————— end #%s HTML —————————',
                            self.id, content.__class__.__name__, encoding,
                            unicode(content, encoding), self.id)
            except:
                LOGGER.exception(u'Could not log source HTML content of '
                                 u'article %s.', self)

        content = STRAINER_EXTRACTOR.feed(content, encoding=encoding)

        # TODO: remove noscript blocks ?
        #
        # TODO: remove ads (after noscript because they
        #       seem to be buried down in them)
        #       eg. <noscript><a href="http://ad.doubleclick.net/jump/clickz.us/ # NOQA
        #       media/media-buying;page=article;artid=2280150;topcat=media;
        #       cat=media-buying;static=;sect=site;tag=measurement;pos=txt1;
        #       tile=8;sz=2x1;ord=123456789?" target="_blank"><img alt=""
        #       src="http://ad.doubleclick.net/ad/clickz.us/media/media-buying; # NOQA
        #       page=article;artid=2280150;topcat=media;cat=media-buying;
        #       static=;sect=site;tag=measurement;pos=txt1;tile=8;sz=2x1;
        #       ord=123456789?"/></a></noscript>

        if config.ARTICLE_FETCHING_DEBUG:
            try:
                LOGGER.info(u'————————— #%s CLEANED %s > %s —————————'
                            u'\n%s\n'
                            u'————————— end #%s CLEANED —————————',
                            self.id, content.__class__.__name__, encoding,
                            unicode(content, encoding), self.id)
            except:
                LOGGER.exception(u'Could not log cleaned HTML content of '
                                 u'article %s.', self)

        return content, encoding

    def fetch_content_text(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_TEXT_DISABLED:
            LOGGER.warning(u'Article text fetching disabled in configuration.')
            return

        if self.content_type == CONTENT_TYPE_NONE:

            LOGGER.info(u'Parsing text content for article %s…', self)

            if self.likely_multipage_content():
                # If everything goes well, 'content' should be an utf-8
                # encoded strings. See the non-paginated version for details.
                content    = ''
                next_link  = self.url
                pages      = 0

                while next_link is not None:
                    pages       += 1
                    current_page, encoding = \
                        self.fetch_content_text_one_page(next_link)
                    content     += str(current_page)
                    next_link    = self.get_next_page_link(current_page)

                    if next_link:
                        self.pages_urls.append(next_link)

                LOGGER.info(u'Fetched %s page(s) for article %s.', pages, self)

            else:
                # first: http://www.crummy.com/software/BeautifulSoup/bs4/doc/#non-pretty-printing # NOQA
                # then: InvalidStringData: strings in documents must be valid UTF-8 (MongoEngine says) # NOQA
                content, encoding = self.fetch_content_text_one_page()

                # Everything should be fine: MongoDB absolutely wants 'utf-8'
                # and BeautifulSoup's str() outputs 'utf-8' encoded strings :-)
                self.content = str(content)

            self.content_type = CONTENT_TYPE_HTML

            if commit:
                self.save()

        #
        # TODO: parse HTML links to find other 1flow articles and convert
        # the URLs to the versions we have in database. Thus, clicking on
        # these links should immediately display the 1flow version, from
        # where the user will be able to get to the public website if he
        # wants. NOTE: this is just the easy part of this idea ;-)
        #

        #
        # TODO: HTML word count here, before markdown ?
        #

        self.convert_to_markdown(force=force, commit=commit)

        LOGGER.info(u'Done parsing content for article %s.', self)

    def convert_to_markdown(self, force=False, commit=True):

        if config.ARTICLE_MARKDOWN_DISABLED:
            LOGGER.warning(u'Article markdown convert disabled in '
                           u'configuration.')
            return

        if self.content_type == CONTENT_TYPE_MARKDOWN and not force:
            LOGGER.warning(u'Article %s already converted to Markdown.', self)
            return

        if self.content_type != CONTENT_TYPE_HTML:
            LOGGER.warning(u'Article %s cannot be converted to Markdown, '
                           u'it is not currently HTML.', self)
            return

        LOGGER.info(u'Converting article %s to markdown…', self)

        try:
            # We decode content to Unicode before converting,
            # and re-encode back to utf-8 before saving. MongoDB
            # accepts only utf-8 data, html2text wants unicode.
            # Everyone should be happy.
            self.content = html2text.html2text(
                self.content.decode('utf-8')).encode('utf-8')

        except Exception, e:
            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Markdown convert failed for article %s.', self)
            return e

        self.content_type = CONTENT_TYPE_MARKDOWN

        #
        # TODO: word count here
        #

        if commit:
            self.save()

        if config.ARTICLE_FETCHING_DEBUG:
            LOGGER.info(u'————————— #%s Markdown %s —————————'
                        u'\n%s\n'
                        u'————————— end #%s Markdown —————————',
                        self.id, self.content.__class__.__name__,
                        self.content, self.id)

    @classmethod
    def signal_post_save_handler(cls, sender, document, **kwargs):
        if kwargs.get('created', False):
            document.post_save_task.delay()

    @celery_task_method(name='Article.post_save', queue='high')
    def post_save_task(self):

        self.slug = slugify(self.title)
        self.save()

        # TODO: create short_url

        # Manually randomize a little the fetching, to avoid
        # http://dev.1flow.net/development/1flow-dev-alternate/group/1243/
        # as much as possible. This is not yet a full-featured solution.
        self.fetch_content.apply_async((), countdown=randrange(5))

        #self.parse_content.delay()
        #self.parse_full_content.delay()

        # TODO: remove_useless_blocks, eg:
        #       <p><a href="http://addthis.com/bookmark.php?v=250">
        #       <img src="http://cache.addthis.com/cachefly/static/btn/
        #       v2/lg-share-en.gif" alt="Bookmark and Share" /></a></p>
        #
        #       (in 51d6a1594adc895fd21c3475, see Notebook)
        #
        # TODO: link_replace (by our short_url_link for click statistics)
        # TODO: images_fetch
        #       eg. handle <img alt="2013-05-17_0009.jpg"
        #           data-lazyload-src="http://www.vcsphoto.com/blog/wp-content/uploads/2013/05/2013-05-17_0009.jpg" # NOQA
        #           src="http://www.vcsphoto.com/blog/wp-content/themes/prophoto4/images/blank.gif" # NOQA
        #           height="1198" sidth="900"/>
        #
        # TODO: authors_fetch
        # TODO: publishers_fetch
        # TODO: duplicates_find

        return


class Read(Document):
    user = ReferenceField('User')
    article = ReferenceField('Article', unique_with='user')
    is_read = BooleanField(default=False)
    is_auto_read = BooleanField(default=False)
    date_created = DateTimeField(default=now)
    date_read = DateTimeField()
    date_auto_read = DateTimeField()
    tags = ListField(StringField())

    # This will be set to Article.default_rating
    # until the user sets it manually.
    rating = FloatField()

    # For free users, fix a limit ?
    #meta = {'max_documents': 1000, 'max_size': 2000000}

    @classmethod
    def signal_pre_save_handler(cls, sender, document, **kwargs):

        document.rating = document.article.default_rating

    def __unicode__(self):
        return _(u'%s∞%s (#%s) %s %s') % (
            self.user, self.article, self.id,
            _(u'read') if self.is_read else _(u'unread'), self.rating)


class Comment(Document):
    TYPE_COMMENT = 1
    TYPE_INSIGHT = 10
    TYPE_ANALYSIS = 20
    TYPE_SYNTHESIS = 30

    VISIBILITY_PUBLIC = 1
    VISIBILITY_GROUP = 10
    VISIBILITY_PRIVATE = 20

    nature = IntField(default=TYPE_COMMENT)
    visibility = IntField(default=VISIBILITY_PUBLIC)

    is_synthesis = BooleanField()
    is_analysis = BooleanField()
    content = StringField()

    feedback = EmbeddedDocumentField(FeedbackDocument)

    # We don't comment reads. We comment articles.
    #read = ReferenceField('Read')
    article = ReferenceField('Article')

    # Thus, we must store
    user = ReferenceField('User')

    in_reply_to = ReferenceField('Comment')  # , null=True)

    # @property
    # def type(self):
    #     return self.internal_type
    # @type.setter
    # def type(self, type):
    #     parent_type = comment.in_reply_to.type
    #     if parent_type is not None:
    #         if parent_type == Comment.TYPE_COMMENT:
    #             if type == Comment.TYPE_COMMENT:
    #                 self.internal_type = Comment.TYPE_COMMENT
    #             raise ValueError('Cannot synthetize a comment')
    #             return Comment.TYPE_COMMENT


class SnapPreference(Document):
    select_paragraph = BooleanField(_('Select whole paragraph on click'),
                                    default=False)  # , blank=True)
    default_public = BooleanField(_('Grows public by default'),
                                  default=True)  # , blank=True)


class NotificationPreference(Document):
    """ Email and other web notifications preferences. """


class Preference(Document):
    snap = EmbeddedDocumentField('SnapPreference')
    notification = EmbeddedDocumentField('NotificationPreference')


class User(Document):
    django_user = IntField(unique=True)
    username    = StringField()
    first_name  = StringField()
    last_name   = StringField()
    preferences = ReferenceField('Preference')

    def __unicode__(self):
        return u'%s #%s (Django ID: %s)' % (self.username or u'<UNKNOWN>',
                                            self.id, self.django_user)

    def get_full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    @classmethod
    def signal_post_save_handler(cls, sender, document, **kwargs):
        if kwargs.get('created', False):
            document.post_save_task.delay()

    @celery_task_method(name='User.post_save', queue='high')
    def post_save_task(self):

        django_user = User.objects.get(id=self.django_user)
        self.username = django_user.username
        self.last_name = django_user.last_name
        self.first_name = django_user.first_name
        self.save()


connect_mongoengine_signals(globals())
