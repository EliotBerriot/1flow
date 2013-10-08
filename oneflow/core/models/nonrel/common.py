# -*- coding: utf-8 -*-
"""


    .. note:: as of Celery 3.0.20, there are many unsolved problems related
        to tasks-as-methods. Just to name a few:
        - https://github.com/celery/celery/issues/1458
        - https://github.com/celery/celery/issues/1459
        - https://github.com/celery/celery/issues/1478

        As I have no time to dive into celery celery and fix them myself,
        I just turned tasks-as-methods into standard tasks calling the "old"
        method inside the task.

        This has the side-effect-benefit of avoiding any `.reload()` call
        inside the tasks methods themselves, but forces us to write extraneous
        functions only for the tasks, which is duplicate work for me.

        But in the meantime, this allows tests to work correctly, which is
        a much bigger benefit.

    .. warning:: **convention** says tasks that call `Class.method()` must
        be named `class_method()` (``class`` as lowercase). Lookups rely on
        this.

        And special post-create tasks must be
        named ``def class_post_create_task()``, not
        just ``class_article_post_create``. This is because these special
        methods are not meant to be called in the app normal life, only at a
        special moment (after database record creation, exactly).
        BUT, I prefer the ``name=`` of the celery task to stay without
        the ``_task`` for shortyness and readability in celery flower.
"""

import os
import errno
import logging
import requests

from statsd import statsd
from constance import config

from django.conf import settings
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••• constants and setup


LOGGER = logging.getLogger(__name__)

REQUEST_BASE_HEADERS  = {'User-agent': settings.DEFAULT_USER_AGENT}

# Lower the default, we know good websites just work well.
requests.adapters.DEFAULT_RETRIES = 1

# Don't use any lang-dependant values (eg. _(u'NO CONTENT'))
CONTENT_NOT_PARSED       = None
CONTENT_TYPE_NONE        = 0
CONTENT_TYPE_HTML        = 1
# Since Hotfix 0.20.11.5, we process markdown differently,
# And need to know about the "old" processing method to be
# able to fix it afterwards in the production database.
CONTENT_TYPE_MARKDOWN_V1 = 2
CONTENT_TYPE_MARKDOWN    = 3
CONTENT_TYPE_IMAGE       = 100
CONTENT_TYPE_VIDEO       = 200
CONTENT_TYPES_FINAL      = (CONTENT_TYPE_MARKDOWN,
                            CONTENT_TYPE_MARKDOWN_V1,
                            CONTENT_TYPE_IMAGE,
                            CONTENT_TYPE_VIDEO,
                            )

CONTENT_PREPARSING_NEEDS_GHOST = 1
CONTENT_FETCH_LIKELY_MULTIPAGE = 2

# MORE CONTENT_PREPARSING_NEEDS_* TO COME

ORIGIN_TYPE_NONE          = 0
ORIGIN_TYPE_GOOGLE_READER = 1
ORIGIN_TYPE_FEEDPARSER    = 2
ORIGIN_TYPE_STANDALONE    = 3
ORIGIN_TYPE_TWITTER       = 4

ARTICLE_ORPHANED_BASE = u'http://{0}/orphaned/article/'.format(
                        settings.SITE_DOMAIN)


class NotTextHtmlException(Exception):
    """ Raised when the content of an article is not text/html, to switch to
        other parsers, without re-requesting the actual content. """
    def __init__(self, message, response):
        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)
        self.response = response


class DocumentHelperMixin(object):
    """ Because, as of MongoEngine 0.8.3,
        subclassing `Document` is not possible o_O

        […]
          File "/Users/olive/sources/1flow/oneflow/core/models/nonrel.py", line 141, in <module> # NOQA
            class Source(Document):
          File "/Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/base/metaclasses.py", line 332, in __new__ # NOQA
            new_class = super_new(cls, name, bases, attrs)
          File "/Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/base/metaclasses.py", line 120, in __new__ # NOQA
            base.__name__)
        ValueError: Document Document may not be subclassed

    """

    # HACK: this variable must be set to the nonrel.__init__.globals()
    # dict, else duplication will not work because of module confinment.
    # We can't import every module here, this would create import loops
    # because every nonrel object inherits from this very class.
    nonrel_globals = None

    @property
    def _db_name(self):
        return self._get_db().name

    @classmethod
    def get_or_404(cls, oid):
        """ Rough equivalent of Django's get_object_or_404() shortcut.
            Not as powerful, though.

            .. versionadded:: 0.21.7
        """

        try:
            return cls.objects.get(id=oid)

        except cls.DoesNotExist:
            raise Http404(_(u'{0} #{1} not found').format(cls.__name__, oid))

        except:
            LOGGER.exception(u'Exception while getting %s #%s',
                             cls.__name__, oid)
            raise

    def register_duplicate(self, duplicate, force=False):

        # be sure this helper method is called
        # on a document that has the atribute.
        assert hasattr(duplicate, 'duplicate_of')

        _cls_name_ = self.__class__.__name__

        # TODO: get this from a class attribute?
        # I'm not sure for MongoEngine models.
        lower_plural = _cls_name_.lower() + u's'

        if duplicate.duplicate_of:
            if duplicate.duplicate_of != self:
                # NOTE: for Article, this situation can't happen IRL
                # (demonstrated with Willian 20130718).
                #
                # Any "second" duplicate *will* resolve to the master via the
                # redirect chain. It will *never* resolve to an intermediate
                # URL in the chain.
                #
                # For other objects it should happen too, because the
                # `get_or_create()` methods should return the `.duplicate_of`
                # attribute if it is not None.

                LOGGER.warning(u'%s %s is already a duplicate of '
                               u'another instance, not %s. Aborting.',
                               _cls_name_, duplicate, duplicate.duplicate_of)
                return

        LOGGER.info(u'Registering %s %s as duplicate of %s…',
                    _cls_name_, duplicate, self)

        # Register the duplication immediately, for other
        # background operations to use ourselves as value.
        duplicate.duplicate_of = self
        duplicate.save()

        statsd.gauge('%s.counts.duplicates' % lower_plural, 1, delta=True)

        try:
            # Having tasks not as methods because of Celery bugs forces
            # us to do strange things. We have to "guess" and lookup the
            # task name in the current module. OK, not *that* big deal.
            self.nonrel_globals[self.__class__.__name__.lower()
                                + '_replace_duplicate_everywhere'].delay(
                                    self.id, duplicate.id)

        except KeyError:
            LOGGER.warning(u'Object %s does not have a '
                           u'`replace_duplicate_everywhere()` task.', self)

    def offload_attribute(self, attribute_name, remove=False):
        """ NOTE: this method is not used as of 20130816, but I keep it because
            it contains the base for the idea of a global on-disk unique path
            for each document.

            The unique path can also eventually be used for statistics, to
            avoid unbrowsable too big folders in Graphite.
        """

        # TODO: factorize this sometwhere common to all classes.
        object_path = os.path.join(self.__class__.__name__,
                                   self.id[-1] + self.id[-2],
                                   self.id[-3] + self.id[-4],
                                   self.id[-5] + self.id[-6],
                                   self.id[-7] + self.id[-8],
                                   self.id)

        offload_directory = config.ARTICLE_OFFLOAD_DIRECTORY.format(
            object_path=object_path)

        if not os.path.exists(offload_directory):
            try:
                os.makedirs(offload_directory)

            except (OSError, IOError), e:
                if e.errno != errno.EEXIST:
                    raise

        with open(os.path.join(offload_directory, attribute_name), 'w') as f:
            f.write(getattr(self, attribute_name))

        if remove:
            delattr(self, attribute_name)

    def safe_reload(self):
        try:
            self.reload()

        except:
            pass


class DocumentTreeMixin(object):
    """ WARNING: currently I have no obvious way to add the required
        fields to the class this mixin is added to. The two fields
        ``.parent`` and ``.children`` must exist.

        See the :class:`Folder` class for an example. The basics are::

            parent = ReferenceField('self', reverse_delete_rule=NULLIFY)
            children = ListField(ReferenceField('self',
                                 reverse_delete_rule=PULL), default=list)

    """

    def set_parent(self, parent, update_reverse_link=True, full_reload=True):

        self.update(set__parent=parent)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            parent.add_child(self, update_reverse_link=False)

    def unset_parent(self, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            self.parent.remove_child(self, update_reverse_link=False)

        self.update(unset__parent=True)

        if full_reload:
            self.safe_reload()

    def add_child(self, child, update_reverse_link=True, full_reload=True):
        self.update(add_to_set__children=child)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            child.set_parent(self, update_reverse_link=False)

    def remove_child(self, child, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            child.unset_parent(self, update_reverse_link=False)

        self.update(pull__children=child)

        if full_reload:
            self.safe_reload()