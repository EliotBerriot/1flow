# -*- coding: utf-8 -*-

import time
import requests
import logging
import datetime
import html2text
import feedparser
import simplejson as json

try:
    from boilerpipe.extract import Extractor as BoilerPipeExtractor

except ImportError:
    BoilerPipeExtractor = None

from celery.contrib.methods import task as celery_task_method

from pymongo.errors import DuplicateKeyError

from mongoengine import Document
from mongoengine.errors import OperationError, NotUniqueError
from mongoengine.fields import (IntField, FloatField, BooleanField,
                                DateTimeField,
                                ListField, StringField,
                                URLField,
                                ReferenceField, GenericReferenceField,
                                EmbeddedDocumentField)

from django.utils.translation import ugettext_lazy as _
from django.utils.text        import slugify

from ...base.utils import (connect_mongoengine_signals,
                           SimpleCacheLock, AlreadyLockedException,
                           HttpResponseLogProcessor)
from .keyval import FeedbackDocument

LOGGER = logging.getLogger(__name__)

feedparser.USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' # NOQA

CONTENT_NOT_PARSED    = None  # Don't use any _() (fails) nor any lang-dependant values.
CONTENT_TYPE_NONE     = 0
CONTENT_TYPE_HTML     = 1
CONTENT_TYPE_MARKDOWN = 2

now       = datetime.datetime.now
#today     = datetime.date.today
timedelta = datetime.timedelta

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
    name           = StringField()
    url            = URLField(unique=True)
    site_url       = URLField()
    slug           = StringField()
    restricted     = BooleanField(default=False)

    fetch_interval = IntField(default=1800)
    last_fetch     = DateTimeField(default=now)

    # Stored directly from feedparser data to avoid wasting BW.
    last_etag      = StringField()
    last_modified  = StringField()

    def __unicode__(self):
        return _(u'%s (#%s) from %s') % (self.name, self.id, self.url)

    @classmethod
    def signal_post_save_handler(cls, sender, document, **kwargs):

        # Update the feed with current content.
        self.refresh.delay()

    def get_latest_article(self):

        latest = Article.objects.filter(
            feed__in=(self,)).order_by('-date_published').limit(1)

        try:
            return latest[0]

        except:
            return None

    def get_subscribers(self):
        return [
            s.user
            for s in Subscription.objects.filter(feed__in=(self,))
        ]

    def create_article_and_reads(self, article, subscribers, tags):
        """ Take a feedparser item and lists of Feed subscribers and
            tags, then create the corresponding Article and Read(s). """

        content = getattr(article, 'content', CONTENT_NOT_PARSED)

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
            feed=self)

        # If the article was not created, reads creation are likely
        # to fail too. Don't display warnings, they are quite boring.
        new_article.create_reads(subscribers, tags, verbose=created)

    @celery_task_method(name='Feed.check_refresher', queue='medium')
    def check_refresher(self):

        my_lock = SimpleCacheLock(self)

        if my_lock.acquire():
            # no refresher is running.
            # Release the lock and launch one.
            my_lock.release()

            self.refresh.delay()

    @celery_task_method(name='Feed.refresh', queue='low')
    def refresh(self, force=False):
        """ Find new articles in an RSS feed.

            .. note:: we don't release the lock, this is intentional. The
                next refresh should not occur within the feed official
                refresh interval, this would waste resources.
        """

        my_lock = SimpleCacheLock(self)

        if not my_lock.acquire():
            if force:
                LOGGER.warning(u'Forcing reschedule of fetcher for feed %s.',
                               self)
                my_lock.release()
                my_lock.acquire()
            else:
                LOGGER.info(u'Refresh for %s already scheduled, aborting.', self)
                return

        if self.last_fetch is not None and self.last_fetch >= (now()
                - timedelta(seconds=self.fetch_interval)):
            if force:
                LOGGER.warning(u'Forcing refresh of recently fetched feed %s.',
                               self)
            else:
                LOGGER.info(u'Last refresh of feed %s too recent, aborting.', self)
                return

        # Launch the next fetcher right now, in order for the duration
        # of the current fetch not to delay the next and make the actual
        # fetch interval be longer than advertised.
        self.refresh.apply_async(countdown=self.fetch_interval)

        LOGGER.info(u'Refreshing feed %s…', self)

        kwargs = {}

        # Implement last-modified & etag headers to save BW.
        # Cf. http://pythonhosted.org/feedparser/http-etag.html
        if self.last_modified:
            kwargs['modified'] = self.last_modified

        else:
            latest_article = self.get_latest_article()
            latest_date    = getattr(latest_article, 'date_published', None)

            if latest_date:
                kwargs['modified'] = latest_date

        if self.last_etag:
            kwargs['etag'] = self.last_etag

        http_logger        = HttpResponseLogProcessor()
        kwargs['referrer'] = self.site_url
        kwargs['handlers'] = [http_logger]

        parsed_feed = feedparser.parse(self.url, **kwargs)

        # In case of a redirection, just check the last hop HTTP status.
        if http_logger.log[-1]['status'] != 304:

            # Store these for next cycle.
            self.last_modified = parsed_feed.modified
            self.last_etag     = getattr(parsed_feed, 'etag', None)

            subscribers = self.get_subscribers()
            tags        = getattr(parsed_feed, 'tags', [])

            for article in parsed_feed.entries:
                self.create_article_and_reads(article, subscribers, tags)

        else:
            LOGGER.info(u'No new content in feed %s', self)

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
    title = StringField(max_length=256, required=True)
    slug = StringField(max_length=256)
    authors = ListField(ReferenceField('User'))
    publishers = ListField(ReferenceField('User'))
    url = URLField(unique=True)
    date_published = DateTimeField()
    abstract = StringField()
    language = StringField()
    text_direction = StringField()
    comments = ListField(ReferenceField('Comment'))
    default_rating = FloatField(default=0.0)

    content      = StringField(default=CONTENT_NOT_PARSED)
    content_type = IntField(default=CONTENT_TYPE_NONE)
    full_content      = StringField(default=CONTENT_NOT_PARSED)
    full_content_type = IntField(default=CONTENT_TYPE_NONE)

    # This should go away soon, after a full re-parsing.
    google_reader_original_data = StringField()

    # A snap / a serie of snaps references the original article.
    # An article references its source (origin blog / newspaper…)
    source = GenericReferenceField()

    feed = ReferenceField('Feed')

    # Avoid displaying duplicates to the user.
    duplicates = ListField(ReferenceField('Article'))  # , null=True)

    def __unicode__(self):
        return _(u'%s (#%s) from %s') % (self.title, self.id, self.url)

    def is_origin(self):
        return isinstance(self.source, Source)

    def create_reads(self, users, tags, verbose=True):

        for user in users:
            new_read = Read(article=self,
                         user=user,
                         tags=tags)
            try:
                new_read.save(validate=False)

            except (NotUniqueError, DuplicateKeyError):
                if verbose:
                    LOGGER.warning(u'Duplicate read %s!', new_read)

            except:
                LOGGER.exception(u'Could not save read %s!', new_read)

    @classmethod
    def create_article(cls, title, url, feed, **kwargs):

        LOGGER.warning('trying %s', url)

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

    @celery_task_method(name='Article.parse_content',
                        queue='low', default_retry_delay=3600)
    def parse_content(self, force=False, commit=True):

        if self.content_type == CONTENT_TYPE_MARKDOWN and not force:
            LOGGER.warning(u'Article %s has already been parsed.', self)
            return

        elif self.content_type == CONTENT_TYPE_NONE:

            if not BoilerPipeExtractor:
                raise self.parse_content.retry(
                    exc=RuntimeError(u'BoilerPipeExtractor not found '
                                     u'(or JPype not installed?)'))

            LOGGER.info(u'Parsing content for article %s…', self)

            try:
                extractor = BoilerPipeExtractor(extractor='ArticleExtractor',
                                                url=self.url)
                self.content = extractor.getHTML()

            except Exception, e:
                # TODO: except urllib2.error: retry with longer delay.

                LOGGER.exception(u'BoilerPipe extraction failed for '
                                 u'article %s.', self)
                raise self.parse_content.retry(exc=e)

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

        try:
            self.content = html2text.html2text(extracted_html)

        except Exception, e:
            LOGGER.exception(u'Markdown shrink failed for article %s.', self)
            raise self.parse_content.retry(exc=e)

        self.content_type = CONTENT_TYPE_MARKDOWN

        # Until full content is parsed, we have at least the content.
        self.full_content = self.content

        if commit:
            self.save(validate=False)

        self.parse_full_content.delay()

        return self

    @celery_task_method(name='Article.parse_full_content',
                        queue='low', rate_limit='30/m',
                        default_retry_delay=3600)
    def parse_full_content(self, force=False, commit=True):

        if self.full_content_parsed and not force:
            LOGGER.warning(u'Article %s has already been fully parsed.', self)

        LOGGER.info(u'Parsing full content for article %s…', self)

        #
        # TODO: if self.feed.options.multi_pages:
        #           run multiple calls for every page.
        # TODO: run the readability API call…
        # TODO: create our own parser (see NewsBlur / BeautifulSoup)…
        #

        if commit:
            self.save(validate=False)

        return self

    @classmethod
    def signal_post_save_handler(cls, sender, document, **kwargs):

        document.post_save_task.delay()

    @celery_task_method(name='Article.post_save', queue='high')
    def post_save_task(self):

        self.slug = slugify(self.title)
        self.save(validate=False)

        self.parse_content()

        # TODO: images_fetch
        # TODO: authors_fetch
        # TODO: publishers_fetch
        # TODO: duplicates_find
        pass


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
    def signal_post_save_handler(cls, sender, document, **kwargs):

        document.rating = document.article.default_rating
        document.save()

    def __unicode__(self):
        return _(u'%s∞%s (#%s) %s %s') % (self.user, self.article, self.id,
                                          _(u'read') if self.is_read
                                          else _(u'unread'), self.rating)

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
    preferences = ReferenceField('Preference')

connect_mongoengine_signals(globals())
