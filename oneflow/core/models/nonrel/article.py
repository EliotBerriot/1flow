# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import logging
import feedparser

import re
import gc
import ast
import uuid
import requests
import strainer
import html2text

from bs4 import BeautifulSoup
from statsd import statsd
from random import randrange
from constance import config
from markdown_deux import markdown

#from xml.sax import SAXParseException

from celery import task, chain as tasks_chain
from celery.exceptions import SoftTimeLimitExceeded

from humanize.time import naturaldelta
from humanize.i18n import django_language

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY, PULL, CASCADE
from mongoengine.fields import (IntField, StringField, URLField, BooleanField,
                                FloatField, DateTimeField,
                                ListField, ReferenceField, )
from mongoengine.errors import NotUniqueError, ValidationError

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify
from django.template.loader import render_to_string
from django.template.loader import add_to_builtins

from ....base.utils.http import clean_url
from ....base.utils.dateutils import now
from ....base.utils import (detect_encoding_from_requests_response,
                            RedisExpiringLock,
                            StopProcessingException)

from sparks.foundations.classes import SimpleObject

from .common import (DocumentHelperMixin,
                     NotTextHtmlException,
                     CONTENT_NOT_PARSED, CONTENT_TYPE_NONE,
                     CONTENT_TYPE_HTML,
                     CONTENT_TYPE_MARKDOWN_V1, CONTENT_TYPE_MARKDOWN,
                     CONTENT_TYPE_BOOKMARK,
                     CONTENT_TYPES_FINAL,
                     CONTENT_PREPARSING_NEEDS_GHOST,
                     CONTENT_FETCH_LIKELY_MULTIPAGE,
                     ORIGIN_TYPE_NONE,
                     ORIGIN_TYPE_FEEDPARSER,
                     ORIGIN_TYPE_WEBIMPORT,
                     ORIGIN_TYPE_GOOGLE_READER,
                     ARTICLE_ORPHANED_BASE,
                     REQUEST_BASE_HEADERS,
                     )

from .tag import Tag
from .source import Source
from .website import WebSite
from .author import Author

LOGGER                = logging.getLogger(__name__)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT


__all__ = ('article_absolutize_url',
           'article_postprocess_original_data',
           'article_replace_duplicate_everywhere',
           'article_find_image',
           'article_fetch_content',
           'article_post_create_task', 'Article', )


# ————————————————————————————————————————————————————————————————— start ghost


if config.FEED_FETCH_GHOST_ENABLED:
    try:
        import ghost
    except:
        ghost = None # NOQA
    else:
        GHOST_BROWSER = ghost.Ghost()


else:
    ghost = None # NOQA


# Until we patch Ghost to use more than one Xvfb at the same time,
# we are tied to ensure there is only one running at a time.
global_ghost_lock = RedisExpiringLock('__ghost.py__')


# ——————————————————————————————————————————————————————————————————— end ghost


@task(name='Article.absolutize_url', queue='swarm', default_retry_delay=3600)
def article_absolutize_url(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.absolutize_url(*args, **kwargs)


@task(name='Article.postprocess_original_data', queue='low')
def article_postprocess_original_data(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.postprocess_original_data(*args, **kwargs)


@task(name='Article.replace_duplicate_everywhere', queue='low')
def article_replace_duplicate_everywhere(article_id, dupe_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    dupe    = Article.objects.get(id=dupe_id)
    return article.replace_duplicate_everywhere(dupe, *args, **kwargs)


@task(name='Article.find_image', queue='fetch', default_retry_delay=3600)
def article_find_image(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.find_image(*args, **kwargs)


@task(name='Article.fetch_content', queue='fetch', default_retry_delay=3600)
def article_fetch_content(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.fetch_content(*args, **kwargs)


@task(name='Article.post_create', queue='high')
def article_post_create_task(article_id, *args, **kwargs):

    article = Article.objects.get(id=article_id)
    return article.post_create_task(*args, **kwargs)


class Article(Document, DocumentHelperMixin):

    title        = StringField(max_length=256, required=True,
                               verbose_name=_(u'Title'))
    slug         = StringField(max_length=256)
    url          = URLField(unique=True, verbose_name=_(u'Public URL'))
    url_absolute = BooleanField(default=False, verbose_name=_(u'Absolute URL'),
                                help_text=_(u'The article URL has been '
                                            u'successfully absolutized '
                                            u'to its unique and final '
                                            u'location.'))
    url_error  = StringField(verbose_name=_(u'URL fetch error'), default=u'',
                             help_text=_(u'Error when absolutizing the URL'))
    pages_urls = ListField(URLField(), verbose_name=_(u'Next pages URLs'),
                           help_text=_(u'In case of a multi-pages article, '
                                       u'other pages URLs will be here.'))
    # not yet.
    #short_url  = URLField(unique=True, verbose_name=_(u'1flow URL'))

    is_restricted = BooleanField(default=False, verbose_name=_(u'restricted'),
                                 help_text=_(u'This article comes from a paid '
                                             u'paid subscription and cannot '
                                             u'be shared like others inside '
                                             u'the platform.'))

    # TODO: rename this field to `is_orphaned`.
    orphaned   = BooleanField(default=False, verbose_name=_(u'Orphaned'),
                              help_text=_(u'This article has no public URL '
                                          u'anymore, or is unfetchable for '
                                          u'some reason.'))

    word_count = IntField(verbose_name=_(u'Word count'))

    authors    = ListField(ReferenceField(u'Author', reverse_delete_rule=PULL))
    publishers = ListField(ReferenceField(u'User', reverse_delete_rule=PULL))

    date_published = DateTimeField(verbose_name=_(u'date published'),
                                   help_text=_(u"When the article first "
                                               u"appeared on the publisher's "
                                               u"website."))
    date_added     = DateTimeField(default=now,
                                   verbose_name=_(u'Date added'),
                                   help_text=_(u'When the article was added '
                                               u'to the 1flow database.'))

    tags = ListField(ReferenceField('Tag', reverse_delete_rule=PULL),
                     default=list, verbose_name=_(u'Tags'),
                     help_text=_(u'Default tags that will be applied to '
                                 u'new reads of this article.'))
    default_rating = FloatField(default=0.0, verbose_name=_(u'default rating'),
                                help_text=_(u'Rating used as a base when a '
                                            u'user has not already rated the '
                                            u'content.'))
    language       = StringField(verbose_name=_(u'Article language'),
                                 max_length=5,
                                 help_text=_(u'2 letters or 5 characters '
                                             u'language code (eg “en”, '
                                             u'“fr-FR”…).'))
    text_direction = StringField(verbose_name=_(u'Text direction'),
                                 choices=((u'ltr', _(u'Left-to-Right')),
                                          (u'rtl', _(u'Right-to-Left'))),
                                 default=u'ltr', max_length=3)

    image_url     = StringField(verbose_name=_(u'image URL'))

    excerpt       = StringField(verbose_name=_(u'Excerpt'),
                                help_text=_(u'Small excerpt of content, '
                                            u'if applicable.'))

    content       = StringField(default=CONTENT_NOT_PARSED,
                                verbose_name=_(u'Content'),
                                help_text=_(u'Article content'))
    content_type  = IntField(default=CONTENT_TYPE_NONE,
                             verbose_name=_(u'Content type'),
                             help_text=_(u'Type of article content '
                                         u'(text, image…)'))
    content_error = StringField(verbose_name=_(u'Error'), default=u'',
                                help_text=_(u'Error when fetching content'))

    # A snap / a serie of snaps references the original article.
    # An article references its source (origin blog / newspaper…)
    source = ReferenceField('self', reverse_delete_rule=NULLIFY)

    origin_type = IntField(default=ORIGIN_TYPE_NONE,
                           verbose_name=_(u'Origin type'),
                           help_text=_(u'Origin of article (feedparser, '
                                       u'twitter, websnap…). Can be 0 '
                                       u'(none/unknown).'))

    # The reverse delete rule is registered in
    # nonrel.feed to avoid an import loop.
    feeds = ListField(ReferenceField('Feed'), default=list)

    comments_feed = URLField()

    @property
    def feed(self):
        """ return the first available feed for this article (an article can
            be mutualized in many RSS feeds and thus have more than one).

            .. note:: Can be ``None``, for example if the user snapped an
                article directly from a standalone web page in browser.
        """

        try:
            return self.feeds[0]

        except IndexError:
            return None

    # Allow quick find of duplicates if we ever want to delete them.
    duplicate_of = ReferenceField('Article', verbose_name=_(u'Duplicate of'),
                                  help_text=_(u'This article is a duplicate of '
                                              u'another, which is referenced '
                                              u'here. Even if they have '
                                              u'different URLs (eg. one can be '
                                              u'shortened, the other not), '
                                              u'they lead to the same final '
                                              u'destination on the web.'),
                                  reverse_delete_rule=NULLIFY)

    meta = {
        'indexes': [
            'content_type',
            'content_error',
            'url_error',
            'date_published',
            {'fields': ('duplicate_of', ), 'sparse': True},
            {'fields': ('source', ), 'sparse': True}

        ]
    }

    def __unicode__(self):
        return _(u'{0} (#{1}) from {2}').format(
            self.title[:40] + (self.title[40:] and u'…'), self.id, self.url)

    def validate(self, *args, **kwargs):
        try:
            super(Article, self).validate(*args, **kwargs)

        except ValidationError as e:
            title_error = e.errors.get('title', None)

            if title_error and str(title_error).startswith(
                    'String value is too long'):
                self.title = self.title[:255] + (self.title[:255] and u'…')
                e.errors.pop('title')

            tags_error = e.errors.get('tags', None)

            if tags_error and 'GenericReferences can only contain documents' \
                    in str(tags_error):

                self.tags = [t for t in self.tags if t is not None]
                e.errors.pop('tags')

            comments_error = e.errors.get('comments_feed', None)

            if comments_error and self.comments_feed == '':
                # Oh please, don't bother me.
                self.comments_feed = None
                e.errors.pop('comments_feed')

            language_error = e.errors.get('language', None)

            if language_error and self.language in (u'', None):
                # Oh please, don't bother me.
                # Again, required=False doesn't work at all.
                e.errors.pop('language')

            if e.errors:
                raise e

    def is_origin(self):
        return isinstance(self.source, Source)

    @property
    def date_published_delta(self):

        with django_language():
            return _(u'{0} ago').format(naturaldelta(self.date_published))

    @property
    def word_count_TRANSIENT(self):
        """ TRANSIENT: until we store the words count, which implies to
            be able to compute it correctly, we do all the work here. """

        if self.word_count:
            return self.word_count

        else:
            if self.content_type in CONTENT_TYPES_FINAL:

                # TODO: exclude video / audio...

                if len(self.content) > config.READ_ARTICLE_MIN_LENGTH:
                    return len(self.content.split())

        return None

    @property
    def get_source(self):

        if self.source:
            return self.source

        if self.feeds:
            return self.feeds

        return _(u'Unknown source')

    @property
    def get_source_unicode(self):

        source = self.get_source

        if source.__class__ in (unicode, str):
            return source

        sources_count = len(source)

        if sources_count > 2:
            return _(u'Multiple sources ({0} feeds)').format(sources_count)

        return u' / '.join(x.name for x in source)

    @property
    def original_data(self):
        try:
            return OriginalData.objects.get(article=self)

        except OriginalData.DoesNotExist:
            return OriginalData(article=self).save()

    def add_original_data(self, name, value):
        od = self.original_data

        setattr(od, name, value)
        od.save()

    def remove_original_data(self, name):
        od = self.original_data

        try:
            delattr(od, name)

        except AttributeError:
            pass

        else:
            od.save()

    def make_excerpt(self, save=False):
        """ This method assumes a markdown content. Test it before calling.

            References:

            http://fr.wikipedia.org/wiki/Droit_de_courte_citation
        """

        if self.content:
            content_length = len(self.content)

            if content_length < config.READ_ARTICLE_MIN_LENGTH:
                return None

            min_threshold = config.EXCERPT_PARAGRAPH_MIN_LENGTH
            ten_percent   = content_length / 10
            paragraphs    = [p for p in self.content.split('\n') if p]
            skipped_text  = False

            for index, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()

                if paragraph.startswith(u'[') or paragraph.startswith(u'!['):
                    continue

                if len(paragraph) < min_threshold:
                    skipped_text = True
                    continue

                retest_lenght = True

                # Strip out images, then links, if any.
                # Striping images before links is mandatory to
                # avoid RE clash on images contained in links.
                try:
                    paragraph = re.sub(ur'\![[]([^]]+)[]][(][^)]+[)]',
                                       # Don't miss the “r” on repl,
                                       # else \1 group doesn't work.
                                       ur'\1', paragraph)
                except IndexError:
                    # No image.
                    pass

                try:
                    paragraph = re.sub(ur'[[]([^]]+)[]][(][^)]+[)]',
                                       # Don't miss the “r” on repl,
                                       # else \1 group doesn't work.
                                       ur'\1', paragraph)
                except IndexError:
                    # No link found in this paragraph.
                    retest_lenght = False

                try:
                    while paragraph[0] == u'#':
                        paragraph = paragraph[1:]

                except IndexError:
                    # The paragraph is empty.
                    continue

                # Re-test the length now that we don't have any link anymore.
                if retest_lenght and len(paragraph) < min_threshold:
                    skipped_text = True
                    continue

                while len(paragraph) > ten_percent:
                    paragraph = u' '.join(paragraph.split(u' ')[:-1])

                try:
                    final_excerpt = markdown(paragraph).strip()

                except:
                    return None

                else:
                    if skipped_text:
                        if final_excerpt.startswith(u'<p>'):
                            final_excerpt = final_excerpt[3:]

                        # Beware the intended ending space
                        final_excerpt = (u'<p><span class="muted">[…]</span> '
                                         + final_excerpt)

                    if index < len(paragraphs):
                        if final_excerpt.endswith(u'</p>'):
                            final_excerpt = final_excerpt[:-4]

                        # Beware the intended starting space
                        final_excerpt += u' <span class="muted">[…]</span></p>'

                    if save:
                        self.excerpt = final_excerpt
                        self.save()

                    return final_excerpt

        return None

    def absolutize_url_must_abort(self, force=False, commit=True):

        if config.ARTICLE_ABSOLUTIZING_DISABLED:
            LOGGER.info(u'Absolutizing disabled by configuration, aborting.')
            return True

        if self.url_absolute and not force:
            LOGGER.info(u'URL of article %s is already absolute!', self)
            return True

        if self.orphaned and not force:
            LOGGER.warning(u'Article %s is orphaned, absolutization aborted.',
                           self)
            return True

        if self.url_error:
            if force:
                self.url_error = u''

                if commit:
                    self.save()
            else:
                LOGGER.warning(u'Article %s already has an URL error, '
                               u'aborting absolutization (currently: %s).',
                               self, self.url_error)
                return True

        return False

    def absolutize_url_post_process(self, requests_response):

        url = requests_response.url

        try:
            proto, host_and_port, remaining = WebSite.split_url(url)

        except ValueError:
            return url

        if 'da.feedsportal.com' in host_and_port:
            # Sometimes the redirect chain breaks and gives us
            # a F*G page with links in many languages "click here
            # to continue".
            bsoup = BeautifulSoup(requests_response.content)

            for anchor in bsoup.findAll('a'):
                if u'here to continue' in anchor.text:
                    return clean_url(anchor['href'])

            # If we come here, feed portal template has probably changed.
            # Developers should be noticed about it.
            LOGGER.critical(u'Feedsportal post-processing failed '
                            u'for article %s (no redirect tag found '
                            u'at address %s)!', self, url)

        # if nothing matched before, just clean the
        # last URL we got. Better than nothing.
        return clean_url(requests_response.url)

    def absolutize_url(self, requests_response=None, force=False, commit=True):
        """ Make the current article URL absolute. Eg. transform:

            http://feedproxy.google.com/~r/francaistechcrunch/~3/hEIhLwVyEEI/

            into:

            http://techcrunch.com/2013/05/18/hell-no-tumblr-users-wont-go-to-yahoo/ # NOQA
                ?utm_source=feeurner&utm_medium=feed&utm_campaign=Feed%3A+francaistechcrunch+%28TechCrunch+en+Francais%29 # NOQA

            and then remove all these F*G utm_* parameters to get a clean
            final URL for the current article.

            Returns ``True`` if the operation succeeded, ``False`` if the
            absolutization pointed out that the current article is a
            duplicate of another. In this case the caller should stop its
            processing because the current article will be marked for deletion.

            Can also return ``None`` if absolutizing is disabled globally
            in ``constance`` configuration.
        """

        # Another example: http://rss.lefigaro.fr/~r/lefigaro/laune/~3/7jgyrQ-PmBA/story01.htm # NOQA

        # ALL celery task methods need to reload the instance in case
        # we added new attributes before the object was pickled to a task.
        self.safe_reload()

        if self.absolutize_url_must_abort(force=force, commit=commit):
            return

        if requests_response is None:
            try:
                requests_response = requests.get(self.url,
                                                 headers=REQUEST_BASE_HEADERS)

            except requests.ConnectionError, e:
                statsd.gauge('articles.counts.url_errors', 1, delta=True)
                self.url_error = str(e)
                self.save()

                LOGGER.error(u'Connection failed while absolutizing URL or %s.',
                             self)
                return

        if not requests_response.ok or requests_response.status_code != 200:

            message = u'HTTP Error %s (%s) while resolving %s.'
            args = (requests_response.status_code, requests_response.reason,
                    requests_response.url)

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.orphaned', 1, delta=True)
                spipe.gauge('articles.counts.url_errors', 1, delta=True)

            self.orphaned  = True
            self.url_error = message % args
            self.save()

            LOGGER.error(message, *args)
            return

        #
        # NOTE: we could also get it eventually from r.headers['link'],
        #       which contains '<another_url>'. We need to strip out
        #       the '<>', and re-absolutize this link, because in the
        #       example it's another redirector. Also r.links is a good
        #       candidate but in the example I used, it contains the
        #       shortlink, which must be re-resolved too.
        #
        #       So: as we already are at the final address *now*, no need
        #       bothering re-following another which would lead us to the
        #       the same final place.
        #

        final_url = self.absolutize_url_post_process(requests_response)

        if final_url != self.url:

            # Just for displaying purposes, see below.
            old_url = self.url

            if self.url_error:
                statsd.gauge('articles.counts.url_errors', -1, delta=True)

            # Even if we are a duplicate, we came until here and everything
            # went fine. We won't need to lookup again the absolute URL.
            statsd.gauge('articles.counts.absolutes', 1, delta=True)
            self.url_absolute = True
            self.url_error    = u''

            self.url = final_url

            try:
                self.save()

            except (NotUniqueError, DuplicateKeyError):
                original = Article.objects.get(url=final_url)

                # Just to display the right "old" one in sentry errors and logs.
                self.url = old_url

                LOGGER.info(u'Article %s is a duplicate of %s, '
                            u'registering as such.', self, original)

                original.register_duplicate(self)
                return False

            # Any other exception will raise. This is intentional.
            else:
                LOGGER.info(u'Article %s (#%s) successfully absolutized URL '
                            u'from %s to %s.', self.title, self.id,
                            old_url, final_url)

        else:
            # Don't do the job twice.
            if self.url_error:
                statsd.gauge('articles.counts.url_errors', -1, delta=True)

            statsd.gauge('articles.counts.absolutes', 1, delta=True)
            self.update(set__url_absolute=True, set__url_error='')
            self.safe_reload()

        return True

    def postprocess_original_data(self, force=False, commit=True):

        methods_table = {
            ORIGIN_TYPE_NONE: self.postprocess_guess_origin_data,
            ORIGIN_TYPE_FEEDPARSER: self.postprocess_feedparser_data,
        }

        meth = methods_table.get(self.origin_type, None)

        if meth is None:
            LOGGER.warning(u'No method to post-process origin type %s of '
                           u'article %s.', self.origin_type, self)
            return

        # This is a Celery task. reload the object
        # from the database for up-to-date attributes.
        self.safe_reload()

        meth(force=force, commit=commit)

    def postprocess_guess_origin_data(self, force=False, commit=True):

        need_save = False

        if self.original_data.feedparser_hydrated:
            self.origin_type = ORIGIN_TYPE_FEEDPARSER
            need_save        = True

        elif self.original_data.google_reader_hydrated:
            self.origin_type = ORIGIN_TYPE_GOOGLE_READER
            need_save        = True

        if need_save:
            if commit:
                self.save()

            # Now that we have an origin type, re-run the real post-processor.
            self.postprocess_original_data(force=force, commit=commit)

    def postprocess_feedparser_data(self, force=False, commit=True):
        """ XXX: should disappear when feedparser_data is useless. """

        if self.original_data.feedparser_processed and not force:
            LOGGER.info('feedparser data already post-processed.')
            return

        fpod = self.original_data.feedparser_hydrated

        if fpod:
            if self.tags == [] and 'tags' in fpod:
                tags = list(Tag.get_tags_set((t['term']
                            # Sometimes, t['term'] can be None.
                            # http://dev.1flow.net/webapps/1flow/group/4082/
                            for t in fpod['tags'] if t['term'] is not None),
                    origin=self))

                self.update_tags(tags, initial=True, need_reload=False)
                self.safe_reload()

            if self.authors == []:
                Author.get_authors_from_feedparser_article(fpod,
                                                           set_to_article=self)

            if self.language is None:
                language = fpod.get('summary_detail', {}).get('language', None)

                if language is None:
                    language = fpod.get('title_detail', {}).get(
                        'language', None)

                if language is not None:
                    try:
                        self.language = language.lower()
                        self.save()

                    except:
                        # This happens if the language code of the
                        # feedparser data does not correspond to a
                        # Django setting language we support.
                        LOGGER.exception(u'Cannot set language %s on '
                                         u'article %s.', language, self)

            if self.orphaned:
                # We have a chance to get at least *some* content. It will
                # probably be incomplete, but this is better than nothing.

                detail = fpod.get('summary_detail', {})

                if detail:
                    detail_type = detail.get('type', None)
                    detail_value = detail.get('value', '')

                    # We need some *real* data, though
                    if len(detail_value) > 20:

                        if detail_type == 'text/plain':
                            self.content = detail_value
                            self.content_type = CONTENT_TYPE_MARKDOWN
                            self.save()

                            statsd.gauge('articles.counts.markdown',
                                         1, delta=True)

                        elif detail_type == 'text/html':
                            self.content = detail_value
                            self.content_type = CONTENT_TYPE_HTML
                            self.save()

                            statsd.gauge('articles.counts.html',
                                         1, delta=True)

                            self.convert_to_markdown()

                        else:
                            LOGGER.warning(u'No usable content-type found '
                                           u'while trying to recover article '
                                           u'%s content: %s => "%s".', self,
                                           detail_type, detail_value)
                    else:
                        LOGGER.warning(u'Empty (or nearly) content-type '
                                       u'found while trying to recover '
                                       u'orphaned article %s '
                                       u'content: %s => "%s".', self,
                                       detail_type, detail_value)
                else:
                    LOGGER.warning(u'No summary detail found while trying '
                                   u'to recover orphaned article %s '
                                   u'content.', self)

            if self.comments_feed is None:

                comments_feed_url = fpod.get('wfw_commentrss', None)

                if comments_feed_url:
                    self.comments_feed = comments_feed_url
                    self.save()

            # We don't care anymore, it's already in another database.
            #self.offload_attribute('feedparser_original_data')

        self.original_data.update(set__feedparser_processed=True)

    def postprocess_google_reader_data(self, force=False, commit=True):
        LOGGER.warning(u'postprocess_google_reader_data() is not implemented '
                       u'yet but it was called for article %s!', self)

    def update_tags(self, tags, initial=False, need_reload=True):

        if initial:
            self.update(set__tags=tags)

        else:
            for tag in tags:
                self.update(add_to_set__tags=tag)

        if need_reload:
            self.safe_reload()

        for read in self.reads:
            if initial:
                read.update(set__tags=tags)

            else:
                for tag in tags:
                    read.update(add_to_set__tags=tag)

            if need_reload:
                read.safe_reload()

    def replace_duplicate_everywhere(self, duplicate, force=False):
        """ register :param:`duplicate` as a duplicate content of myself.

            redirect/modify all reads and feeds links to me, keeping all
            attributes as they are.
        """

        need_reload = False

        for feed in duplicate.feeds:
            try:
                self.update(add_to_set__feeds=feed)

            except:
                # We have to continue to replace reads,
                # and reload() at the end of the method.
                LOGGER.exception(u'Could not add feed %s to feeds of '
                                 u'article %s!', feed, self)
            else:
                need_reload = True

        if need_reload:
            self.safe_reload()

        for read in duplicate.reads:
            read.article = self

            try:
                read.save()

            except (NotUniqueError, DuplicateKeyError):
                # Already registered, simply delete the read.
                read.delete()

            except:
                LOGGER.exception(u'Could not replace current article in '
                                 u'read %s by %s!' % (read, self))

        LOGGER.info(u'Article %s replaced by %s everywhere.', duplicate, self)

    @classmethod
    def create_article(cls, title, url, feeds, **kwargs):
        """ Returns ``True`` if article created, ``False`` if a pure duplicate
            (already exists in the same feed), ``None`` if exists but not in
            the same feed. If more than one feed given, only returns ``True``
            or ``False`` (mutualized state is not checked). """

        if url is None:
            reset_url = True
            # Even for a temporary action, we need something unique…
            url = ARTICLE_ORPHANED_BASE + uuid.uuid4().hex

        else:
            reset_url = False
            url = clean_url(url)

        new_article = cls(title=title, url=url)

        try:
            new_article.save()

        except (DuplicateKeyError, NotUniqueError):
            LOGGER.info(u'Duplicate article “%s” (url: %s) in feed(s) %s.',
                        title, url, u', '.join(unicode(f) for f in feeds))

            cur_article = cls.objects.get(url=url)

            created_retval = False

            if len(feeds) == 1 and feeds[0] not in cur_article.feeds:
                # This article is already there, but has not yet been
                # fetched for this feed. It's mutualized, and as such
                # it is considered at partly new. At least, it's not
                # as bad as being a true duplicate.
                created_retval = None

            for feed in feeds:
                cur_article.update(add_to_set__feeds=feed)

            cur_article.safe_reload()

            return cur_article, created_retval

        else:

            tags = kwargs.pop('tags', [])

            if tags:
                new_article.update(add_to_set__tags=tags)
                new_article.safe_reload()

            need_save = False

            if kwargs:
                need_save = True
                for key, value in kwargs.items():
                    setattr(new_article, key, value)

            if reset_url:
                need_save       = True
                new_article.url = \
                    ARTICLE_ORPHANED_BASE + unicode(new_article.id)
                new_article.orphaned = True
                statsd.gauge('articles.counts.orphaned', 1, delta=True)

            if need_save:
                # Need to save because we will reload just after.
                new_article.save()

            if feeds:
                for feed in feeds:
                    new_article.update(add_to_set__feeds=feed)

                new_article.safe_reload()

            LOGGER.info(u'Created %sarticle %s in feed(s) %s.', u'orphaned '
                        if reset_url else u'', new_article,
                        u', '.join(unicode(f) for f in feeds))

            return new_article, True

    def fetch_content_must_abort(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_DISABLED:
            LOGGER.info(u'Article fetching disabled in configuration.')
            return True

        if self.content_type in CONTENT_TYPES_FINAL and not force:
            LOGGER.info(u'Article %s has already been fetched.', self)
            return True

        if self.content_error:
            if force:
                statsd.gauge('articles.counts.content_errors', -1, delta=True)
                self.content_error = u''

                if commit:
                    self.save()

            else:
                LOGGER.warning(u'Article %s has a fetching error, aborting '
                               u'(%s).', self, self.content_error)
                return True

        if self.url_error:
            LOGGER.warning(u'Article %s has an url error. Absolutize it to '
                           u'clear: %s.', self, self.url_error)
            return True

        if self.orphaned and not force:
            LOGGER.warning(u'Article %s is orphaned, cannot fetch.', self)
            return True

        if self.duplicate_of and not force:
            LOGGER.warning(u'Article %s is a duplicate, will not fetch.', self)
            return True

        return False

    def fetch_content(self, force=False, verbose=False, commit=True):

        # In tasks, doing this is often useful, if
        # the task waited a long time before running.
        self.safe_reload()

        if self.fetch_content_must_abort(force=force, commit=commit):
            return

        #
        # TODO: implement switch based on content type.
        #

        try:
            # The first that matches will stop the chain.
            self.fetch_content_bookmark(force=force, commit=commit)

            self.fetch_content_text(force=force, commit=commit)

        except StopProcessingException, e:
            LOGGER.info(u'Stopping processing of article %s on behalf of '
                        u'an internal caller: %s.', self, e)
            return

        except SoftTimeLimitExceeded, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'Extraction took too long for article %s.', self)
            return

        except NotTextHtmlException, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'No text/html to extract in article %s.', self)
            return

        except requests.ConnectionError, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'Connection failed while fetching article %s.', self)
            return

        except Exception, e:
            # TODO: except urllib2.error: retry with longer delay.
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Extraction failed for article %s.', self)
            return

        self.activate_reads(verbose=verbose)

        # No more needed now that Markdown
        # contents are generated asynchronously.
        #self.prefill_cache()

    def prefill_cache(self):
        """
            As of 20131129, this method is not used anymore. We do not
            pre-generate Markdown contents anymore, now that reading lists
            call them one by one.

            // before:
            Make 1flow reading lists fly. Pre-render all possible versions
            of the article template but still, limited to language(s) the
            feed or the article have.
        """

        # We cannot do this outside, this would create an import loop.
        add_to_builtins('django.templatetags.cache')
        add_to_builtins('django.templatetags.i18n')
        add_to_builtins('oneflow.core.templatetags.coretags')

        # build a fake permissions object for the template to be happy.
        perms = SimpleObject()
        #perms.core = SimpleObject()

        context = {
            'article': self,
            'with_index': 1,
            'read_in_list': 1,
            'perms': perms,
        }

        # NOTE: this is a wrong (incomplete) approach. We should gather the
        # distinct languages of all subscribers. As a french reader, I find
        # it very *strange* to get english footers for articles in
        # english-only feeds (“Hey, is this a bug… or what?”).
        #
        # Thus, while we don't have this information yet (it should be
        # computed in the feed, and cached because it will be heavy to
        # get), just generate everything. We have 2 langs, it's not that
        # horrible, besides the fact that it eats RAM.
        languages = [l[0] for l in settings.LANGUAGES]

        # languages = set()
        # dj_langs = [l[0] for l in settings.LANGUAGES]
        #
        # if self.language is None:
        #     for feed in self.feeds:
        #         for lang in feed.languages:
        #             for dj_lang in dj_langs:
        #                 if lang.startswith(dj_lang):
        #                     # we add the Django language code, because the
        #                     # templates / cache switch on this particular
        #                     # value, not the potentially full language code
        #                     # from the article / feed.
        #                     languages.add(dj_lang)
        # else:
        #     languages = [self.language]
        #
        #if languages == set():
        #    languages = dj_langs

        # TODO: with Django 1.6, check if cache is already present or not:
        # https://docs.djangoproject.com/en/dev/topics/cache/#django.core.cache.utils.make_template_fragment_key # NOQA

        #for full_text_value in (True, False):
        #    context['perms'].core.can_read_full_text = full_text_value

        for lang in languages:
            context['LANGUAGE_CODE'] = lang
            render_to_string('snippets/read/article-body.html', context)

    @property
    def is_good(self):
        """ Return ``True`` if the current article
            is ready to be seen by final users. """

        #
        # NOTE: sync the conditions with @Feed.good_articles
        #

        if self.orphaned:
            return False

        if not self.url_absolute:
            return False

        if self.duplicate_of:
            return False

        if self.content_type not in CONTENT_TYPES_FINAL:
            return False

        return True

    def activate_reads(self, force=False, verbose=False, extended_check=False):

        if self.is_good or force:

            bad_reads = self.bad_reads

            if verbose:
                LOGGER.info(u'Article %s activating %s bad reads…',
                            self, bad_reads.count())

            for read in bad_reads:
                try:
                    if extended_check:
                        read.check_subscriptions()

                    # We 'force' to avoid the reverse test in Read.
                    # We already know the article is OK.
                    read.activate(force=True)

                except:
                    # During a check, we cannot activate all reads at once
                    # if some of them have dangling subscriptions references.
                    # But this is harmless, because they will be corrected
                    # later in the global check.
                    LOGGER.exception(u'Activation failed for Read #%s from '
                                     u'Article #%s.', read.id, self.id)

        else:
            if verbose:
                LOGGER.warning(u'Will not activate reads of bad article %s',
                               self)

    def find_image_must_abort(self, force=False, commit=True):

        if self.image_url and not force:
            LOGGER.info(u'Article %s image already found.', self)
            return True

        if not self.content_type in (CONTENT_TYPE_MARKDOWN, ):
            LOGGER.warning(u'Article %s is not in Markdown format, '
                           u'aborting image lookup.', self)
            return True

    def find_image(self, force=False, commit=True):

        # __          __       _____   _   _  _____  _   _   _____
        # \ \        / //\    |  __ \ | \ | ||_   _|| \ | | / ____|
        #  \ \  /\  / //  \   | |__) ||  \| |  | |  |  \| || |  __
        #   \ \/  \/ // /\ \  |  _  / | . ` |  | |  | . ` || | |_ |
        #    \  /\  // ____ \ | | \ \ | |\  | _| |_ | |\  || |__| |
        #     \/  \//_/    \_\|_|  \_\|_| \_||_____||_| \_| \_____|
        #
        # Please modify core.views.article_image() when
        # the current method gets more love inside.

        if self.find_image_must_abort(force=force, commit=commit):
            return

        try:
            for match in re.finditer(ur'![[][^]]+[]][(]([^)]+)[)]',
                                     self.content):
                if match:
                    self.image_url = match.group(1)

                    if commit:
                        self.save()

                    return self.image_url

            if not self.image_url:
                if self.feed and self.feed.default_image_url:
                    self.image_url = self.feed.default_image_url

                    if commit:
                        self.save()

                    return self.image_url

        except Exception:
            LOGGER.exception(u'Image extraction failed for article %s.', self)

        return None

    def fetch_content_image(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_IMAGE_DISABLED:
            LOGGER.info(u'Article video fetching disabled in configuration.')
            return

    def fetch_content_video(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_VIDEO_DISABLED:
            LOGGER.info(u'Article video fetching disabled in configuration.')
            return

    def needs_ghost_preparser(self):

        try:
            # TODO: this should be coming from the website, not the feed.
            return config.FEED_FETCH_GHOST_ENABLED and \
                self.feed.has_option(CONTENT_PREPARSING_NEEDS_GHOST)

        except AttributeError:
            # self.feed can be None…
            return False

    def likely_multipage_content(self):

        try:
            # TODO: this should be coming from the website, not the feed.
            return self.feed.has_option(CONTENT_FETCH_LIKELY_MULTIPAGE)

        except AttributeError:
            # self.feed can be None…
            return False

    def get_next_page_link(self, from_content):
        """ Try to find a “next page” link in the partial content given as
            parameter. """

        #soup = BeautifulSoup(from_content)

        return None

    def prepare_content_text(self, url=None):
        """ :param:`url` should be sinfon the case of multipage content. """

        if url is None:
            fetch_url = self.url

        else:
            fetch_url = url

        if self.needs_ghost_preparser():

            if ghost is None:
                LOGGER.warning(u'Ghost module is not available, content of '
                               u'article %s will be incomplete.', self)
                return requests.get(fetch_url,
                                    headers=REQUEST_BASE_HEADERS).content

                # The lock will raise an exception if it is already acquired.
                with global_ghost_lock:
                    GHOST_BROWSER.open(fetch_url)
                    page, resources = GHOST_BROWSER.wait_for_page_loaded()

                    #
                    # TODO: detect encoding!!
                    #
                    return page

        response = requests.get(fetch_url, headers=REQUEST_BASE_HEADERS)

        content_type = response.headers.get('content-type', u'unspecified')

        if content_type.startswith(u'text/html'):
            encoding = detect_encoding_from_requests_response(response)

            return response.content, encoding

        raise NotTextHtmlException(u"Content is not text/html "
                                   u"but %s." % content_type,
                                   response=response)

    def extract_and_set_title(self, content=None, commit=True):
        """ Try to extract title from the HTML content, and set """

        if content is None:
            if self.content_type == CONTENT_TYPE_HTML:
                content = self.content

            else:
                if self.title and not self.title.endswith(self.url):
                    raise RuntimeError(u'Non-sense to call this method '
                                       u'on an already set title.')

                # Sadly, we have to reget/reparse the content.
                # Hopefully, this is only used in extreme cases,
                # and not the common one.
                content, encoding = self.prepare_content_text(url=self.url)

        try:
            self.title = BeautifulSoup(content).find('title').contents[0]

        except:
            LOGGER.exception(u'Could not extract title of imported '
                             u'article %s', self)

        else:
            LOGGER.info(u'Successfully set title to “%s”', self.title)
            self.slug = slugify(self.title)

        if commit:
            self.save()

        return content

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
                            unicode(str(content), encoding), self.id)
            except:
                LOGGER.exception(u'Could not log source HTML content of '
                                 u'article %s.', self)

        # LOGGER.warning(u'%s %s %s %s %s', self.origin_type,
        #                self.origin_type == ORIGIN_TYPE_WEBIMPORT,
        #                self.title, self.url, self.title.endswith(self.url))

        if self.origin_type == ORIGIN_TYPE_WEBIMPORT \
                and self.title.endswith(self.url):

            LOGGER.warning(u'Setting title of imported item...')
            self.extract_and_set_title(content, commit=False)

        STRAINER_EXTRACTOR = strainer.Strainer(parser='lxml', add_score=True)
        content = STRAINER_EXTRACTOR.feed(content, encoding=encoding)

        del STRAINER_EXTRACTOR
        gc.collect()

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
                            unicode(str(content), encoding), self.id)
            except:
                LOGGER.exception(u'Could not log cleaned HTML content of '
                                 u'article %s.', self)

        return content, encoding

    def fetch_content_bookmark(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_TEXT_DISABLED:
            LOGGER.info(u'Article fetching disabled in configuration.')
            return

        if self.content_type == CONTENT_TYPE_NONE:

            slashes_parts = [p for p in self.url.split(u'/') if p != u'']

            parts_nr = len(slashes_parts)

            if parts_nr > 5:
                # For sure, this is not a bookmark.
                return

            if parts_nr == 2:
                # This is a simple website link. For sure, a bookmark.
                # eg. we got ['http', 'www.mysite.com']

                self.content_type = CONTENT_TYPE_BOOKMARK

            #elif parts_nr < 5:
                # TODO: find a way to ask the user to choose if he wanted
                # to bookmark the website or just fetch the content.

                domain_dotted = slashes_parts[1]
                domain_dashed = domain_dotted.replace(u'.', u'-')

                self.image_url = (u'http://images.screenshots.com/'
                                  u'{0}/{1}-small.jpg').format(
                    domain_dotted, domain_dashed)

                self.content = (u'http://images.screenshots.com/'
                                u'{0}/{1}-large.jpg').format(
                    domain_dotted, domain_dashed)

                if self.origin_type == ORIGIN_TYPE_WEBIMPORT \
                        and self.title.endswith(self.url):

                    LOGGER.info(u'Setting title of imported item...')
                    content = self.extract_and_set_title(commit=False)

                    if content is not None:
                        try:
                            soup = BeautifulSoup(content)
                            for meta in soup.find_all('meta'):
                                if meta.attrs.get('name', 'none').lower() \
                                        == 'description':
                                    self.excerpt = meta.attrs['content']

                        except:
                            LOGGER.exception(u'Could not extract description '
                                             u'of imported bookmark %s', self)

                        else:
                            LOGGER.info(u'Successfully set description to “%s”',
                                        self.excerpt)

                if commit:
                    self.save()

            # TODO: fetch something like
            # http://www.siteencyclopedia.com/{parts[1]}/
            # and put it in the excerpt.

            # TODO: generate a snapshot of the website and store the image.

                raise StopProcessingException(u'Done setting up bookmark '
                                              u'content for article %s.', self)

    def fetch_content_text(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_TEXT_DISABLED:
            LOGGER.info(u'Article text fetching disabled in configuration.')
            return

        if self.content_type == CONTENT_TYPE_NONE:

            LOGGER.info(u'Parsing text content for article %s…', self)

            if self.likely_multipage_content():
                # If everything goes well, 'content' should be an utf-8
                # encoded strings. See the non-paginated version for details.
                content    = u''
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

                # TRICK: `content` is a BS4 Tag, which cannot be
                # "automagically" converted by MongoEngine for
                # some unknown reason. There is also the famous:
                # TypeError: coercing to Unicode: need string or buffer, Tag found # NOQA
                #
                # Thus, we force it to unicode because this is the safe
                # pivot value in Python/MongoEngine, and MongoDB will
                # convert to an utf8 string internally.
                #
                # NOTE: We can be sure of the utf8 encoding, because
                # str(content) outputs utf8, this is documented in BS4.
                #
                self.content = unicode(str(content), 'utf-8')

            self.content_type = CONTENT_TYPE_HTML

            if self.content_error:
                statsd.gauge('articles.counts.content_errors', -1, delta=True)
                self.content_error = u''

            if commit:
                self.save()

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.empty', -1, delta=True)
                spipe.gauge('articles.counts.html', 1, delta=True)

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
            LOGGER.info(u'Article markdown convert disabled in '
                        u'configuration.')
            return

        if self.content_type == CONTENT_TYPE_MARKDOWN:
            if not force:
                LOGGER.info(u'Article %s already converted to Markdown.', self)
                return

            else:
                statsd.gauge('articles.counts.markdown', -1, delta=True)

        elif self.content_type != CONTENT_TYPE_HTML:
            LOGGER.warning(u'Article %s cannot be converted to Markdown, '
                           u'it is not currently HTML.', self)
            return

        LOGGER.info(u'Converting article %s to markdown…', self)

        md_converter = html2text.HTML2Text()

        # Set sane defaults. body_width > 0 breaks
        # some links by inserting \n inside them.
        #
        # MARKDOWN_V1 had [False, False, 78] (=default parameters)
        md_converter.unicode_snob = True
        md_converter.escape_snob  = True
        md_converter.body_width   = 0

        try:
            # NOTE: everything should stay in Unicode during this call.
            self.content = md_converter.handle(self.content)

        except Exception, e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)

            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Markdown convert failed for article %s.', self)
            return e

        self.content_type = CONTENT_TYPE_MARKDOWN

        if self.content_error:
            statsd.gauge('articles.counts.content_errors', -1, delta=True)
            self.content_error = u''

        #
        # TODO: word count here
        #
        self.postprocess_markdown_links(commit=False, force=force)

        if commit:
            self.save()

        with statsd.pipeline() as spipe:
            spipe.gauge('articles.counts.html', -1, delta=True)
            spipe.gauge('articles.counts.markdown', 1, delta=True)

        if config.ARTICLE_FETCHING_DEBUG:
            LOGGER.info(u'————————— #%s Markdown %s —————————'
                        u'\n%s\n'
                        u'————————— end #%s Markdown —————————',
                        self.id, self.content.__class__.__name__,
                        self.content, self.id)

    def postprocess_markdown_links(self, force=False,
                                   commit=True, test_only=False):
        """ Be sure we have no external links without the website part missing,
            else 1flow article internal links all point to 1flow, which makes
            them unusable.

            BTW, if the current article is an "old" markdown V1 one, try to
            repair its links by removing the `\n` inside them.
        """

        if self.content_type == CONTENT_TYPE_MARKDOWN:
            replace_newlines = False

        elif self.content_type == CONTENT_TYPE_MARKDOWN_V1:
            replace_newlines = True

        else:
            LOGGER.debug(u'Skipped non-Markdown article %s.', self)
            return

        website = WebSite.get_from_url(self.url)

        if website is None:
            LOGGER.warning(u'Article %s has no website??? Post-processing '
                           u'aborted.', self)
            return

        website_url = website.url

        def insert_website(link):
            if link.startswith(u'](/') or link.startswith(u'](.'):
                return u'](' + website_url + link[2:]

            else:
                return link

        # Use a copy during the operation to ensure we can start
        # again from scratch in a future call if anything goes wrong.
        content = self.content

        if replace_newlines:
            for repl_src in re.findall(ur'[[][^]]+[]][(]', content):

                # In link text, we replace by a space.
                repl_dst = repl_src.replace(u'\n', u' ')
                content  = content.replace(repl_src, repl_dst)

        for repl_src in re.findall(ur'[]][(][^)]+[)]', content):

            if replace_newlines:
                # In link URLs, we just cut out newlines.
                repl_dst = repl_src.replace(u'\n', u'')
            else:
                repl_dst = repl_src

            repl_dst = clean_url(insert_website(repl_dst))
            content  = content.replace(repl_src, repl_dst)

        if test_only:
            return content

        else:
            # Everything went OK. Put back the content where it belongs.
            self.content = content

            if replace_newlines:
                self.content_type = CONTENT_TYPE_MARKDOWN

            # Disabled until more love is put inside.
            #self.find_image(commit=False, force=force)

            if commit:
                self.save()

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        article = document

        if created:

            # Some articles are created "already orphaned" or duplicates.
            # In the archive database this is more immediate than looking
            # up the database name.
            if not (article.orphaned or article.duplicate_of):
                if article._db_name != settings.MONGODB_NAME_ARCHIVE:
                    article_post_create_task.delay(article.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            self.slug = slugify(self.title)
            self.save()

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.total', 1, delta=True)
                spipe.gauge('articles.counts.empty', 1, delta=True)

        post_absolutize_chain = tasks_chain(
            # HEADS UP: both subtasks are immutable, we just
            # want the group to run *after* the absolutization.
            article_fetch_content.si(self.id),
            article_postprocess_original_data.si(self.id),
        )

        # Randomize the absolutization a little, to avoid
        # http://dev.1flow.net/development/1flow-dev-alternate/group/1243/
        # as much as possible. This is not yet a full-featured solution,
        # but it's completed by the `fetch_limit` thing.
        #
        # Absolutization conditions everything else. If it doesn't succeed:
        #   - no bother trying to post-process author data for example,
        #     because we need the absolutized website domain to make
        #     authors unique and worthfull.
        #   - no bother fetching content: it uses the same mechanisms as
        #     absolutize_url(), and will probably fail the same way.
        #
        # Thus, we link the post_absolutize_chain as a callback. It will
        # be run only if absolutization succeeds. Thanks, celery :-)
        #
        article_absolutize_url.apply_async((self.id, ),
                                           countdown=randrange(5),
                                           link=post_absolutize_chain)

        #
        # TODO: create short_url
        #

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
        # TODO: duplicates_find (content wise, not URL wise)
        #

        return


class OriginalData(Document, DocumentHelperMixin):

    article = ReferenceField('Article', unique=True,
                             reverse_delete_rule=CASCADE)

    # This should go away soon, after a full re-parsing.
    google_reader = StringField()
    feedparser    = StringField()

    # These are set to True to avoid endless re-processing.
    google_reader_processed = BooleanField(default=False)
    feedparser_processed    = BooleanField(default=False)

    meta = {
        'db_alias': 'archive',
    }

    @property
    def feedparser_hydrated(self):
        """ XXX: should disappear when feedparser_data is useless. """

        if self.feedparser:
            return ast.literal_eval(re.sub(r'time.struct_time\([^)]+\)',
                                    '""', self.feedparser))

        return None

    @property
    def google_reader_hydrated(self):
        """ XXX: should disappear when google_reader_data is useless. """

        if self.google_reader:
            return ast.literal_eval(self.google_reader)

        return None


# —————————————————————————————————————————————————————— external bound methods
#                                            Defined here to avoid import loops


def Tag_replace_duplicate_in_articles_method(self, duplicate, force=False):

    #
    # TODO: update search engine indexes…
    #

    for article in Article.objects(tags=duplicate).no_cache():
        for read in article.reads:
            if duplicate in read.tags:
                read.update(pull__tags=duplicate)
                read.update(add_to_set__tags=self)

        article.update(pull__tags=duplicate)
        article.update(add_to_set__tags=self)


Tag.replace_duplicate_in_articles = Tag_replace_duplicate_in_articles_method
