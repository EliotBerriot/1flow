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
import sys
import errno
import logging
import requests

from statsd import statsd
from operator import attrgetter
from constance import config

from mongoengine import Q

from django.conf import settings
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from ....base.utils.dateutils import benchmark

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
ORIGIN_TYPE_WEBIMPORT     = 5

CACHE_ONE_HOUR  = 3600
CACHE_ONE_DAY   = CACHE_ONE_HOUR * 24
CACHE_ONE_WEEK  = CACHE_ONE_DAY * 7
CACHE_ONE_MONTH = CACHE_ONE_DAY * 30

ARTICLE_ORPHANED_BASE = u'http://{0}/orphaned/article/'.format(
                        settings.SITE_DOMAIN)
USER_FEEDS_SITE_URL   = u'http://{0}'.format(settings.SITE_DOMAIN
                                             ) + u'/user/{user.id}/'
WEB_IMPORT_FEED_URL   = USER_FEEDS_SITE_URL + 'imports'


def lowername(objekt):

    return attrgetter('name')(objekt).lower()


class TreeCycleException(Exception):
    pass


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

    @classmethod
    def check_temporary_defect(cls, defect_name, limit=None, progress=None):

        if limit is None:
            # Don't let "Cursor … invalid at server" errors stop us.
            limit = 10000

        if progress is None:
            progress = 100

        if hasattr(cls, defect_name) and hasattr(cls, defect_name + '_done'):

            Q1_params    = {defect_name + '_done__exists': False}
            Q2_params    = {defect_name + '_done': False}
            done_count   = 0
            failed_count = 0
            failed_ids   = []

            def get_count():
                return cls.objects(Q(**Q1_params)
                                   | Q(**Q2_params)).no_cache().count()

            def get_documents_with_limit():
                return cls.objects(Q(**Q1_params)
                                   | Q(**Q2_params)).limit(limit).no_cache()

            LOGGER.info(u'Counting initial `%s` defects on %s…',
                        defect_name, cls.__name__)

            count = get_count()

            if count:
                LOGGER.info(u'Starting check of %s %s against `%s` '
                            u'(each star: %s done)…', count, cls.__name__,
                            defect_name, progress)

            with benchmark(u'Check %s %s against %s' % (
                           count, cls.__name__, defect_name)):

                while count > failed_count:
                    with benchmark(u'Sub-check %s %s against `%s`' % (limit,
                                   cls.__name__, defect_name)):
                        for document in get_documents_with_limit():
                            try:
                                getattr(document, defect_name)()

                            except:
                                # Let's roll. One fail will not stop up.

                                if document.id in failed_ids:
                                    # Don't "continue", we need done_count to
                                    # be updated, and dots to be outputed.
                                    pass

                                else:
                                    failed_ids.append(document.id)
                                    failed_count += 1
                                    sys.stderr.write(u'\n')
                                    LOGGER.exception(u'SKIP: self.%s() failed '
                                                     u'on %s #%s', defect_name,
                                                     cls.__name__, document.id)

                            done_count += 1

                            if done_count % progress == 0:
                                sys.stderr.write(u'*')
                                sys.stderr.flush()

                                if done_count % limit == 0:
                                    sys.stderr.write(u'\n')

                        count = get_count()

                        if done_count % limit != 0:
                            # Last line deserves a newline.
                            sys.stderr.write(u'\n')

        else:
            LOGGER.error(u'Defect `%s` has not the required class '
                         u'attributes on %s.', defect_name, cls.__name__)

    def register_duplicate(self, duplicate, force=False):

        # be sure this helper method is called
        # on a document that has the atribute.
        assert hasattr(duplicate, 'duplicate_of')

        _cls_name_ = self.__class__.__name__
        _cls_name_lower_ = _cls_name_.lower()
        # TODO: get this from a class attribute?
        # I'm not sure for MongoEngine models.
        lower_plural = _cls_name_lower_ + u's'

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
            self.nonrel_globals[_cls_name_lower_
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

    def compute_cached_descriptors(self, **kwargs):

        # TODO: detect descriptors automatically by examining the __class__.

        lower_class = self.__class__.__name__.lower()
        myglobs = self.nonrel_globals

        for what_name in ('all', 'good', 'bad', 'unread',
                          'starred', 'bookmarked'):

            if kwargs.get(what_name, False):
                func_name = (lower_class + '_'
                             + what_name + '_articles_count_default')
                attr_name = what_name + '_articles_count'

                if func_name in myglobs:
                    try:
                        setattr(self, attr_name, myglobs[func_name](self))

                    except:
                        LOGGER.exception(u'%s #%s could not compute %s '
                                         u'properly.', lower_class,
                                         self.id, attr_name)
                else:
                    LOGGER.exception(u'%s #%s was asked to compute %s, '
                                     u'but the compute function "%s()" '
                                     u'does not exist in the `nonrel` '
                                     u'namespace.', lower_class, self.id,
                                     attr_name, func_name)


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

        if parent == self:
            raise RuntimeError('Cannot add %s as parent of itself.', self)

        if self.is_parent_of(parent):
            raise TreeCycleException(_(u'{0} is already in the parent chain of '
                                       u'{1}. Setting the later parent of the '
                                       u'former would result in a cycle and '
                                       u'is not allowed.').format(
                                            self.name, parent.name))

        if self.parent:
            self.unset_parent(full_reload=False)

        self.update(set__parent=parent)

        if full_reload:
            self.reload()

        if update_reverse_link:
            parent.add_child(self, update_reverse_link=False)

    def unset_parent(self, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            self.parent.remove_child(self, update_reverse_link=False)

        self.update(unset__parent=True)

        if full_reload:
            self.reload()

    def add_child(self, child, update_reverse_link=True, full_reload=True):

        if child == self:
            raise RuntimeError('Cannot add %s as a child of itself.', self)

        if child.is_parent_of(self):
            raise TreeCycleException(_(u'{0} is already in the parent chain of '
                                       u'{1}. Setting the later parent of the '
                                       u'former would result in a cycle and '
                                       u'is not allowed.').format(
                                            child.name, self.name))

        self.update(add_to_set__children=child)

        if full_reload:
            self.reload()

        if update_reverse_link:
            child.set_parent(self, update_reverse_link=False)

    def remove_child(self, child, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            child.unset_parent(self, update_reverse_link=False)

        self.update(pull__children=child)

        if full_reload:
            self.reload()

    @property
    def children_by_name(self):

        return sorted(self.children, key=lowername)

    @property
    def children_tree(self):
        """ Returns a list of all direct children and their children.
            Equivalent of flattening the tree recursively. """

        children = PseudoQuerySet(model=self.__class__)

        for child in sorted(self.children, key=lowername):
            #LOGGER.warning('%s appends %s', self.name, child.name)
            children.append(child)
            #LOGGER.warning('%s extends %s', self.name,
            #               [c.name for c in child.children_tree])
            children.extend(child.children_tree)

        #LOGGER.warning('%s\'s children:\n    from: %s\n    to: %s',
        #               self.name,
        #               [c.name for c in self.children],
        #               [c.name for c in children])

        return children

    def is_parent_of(self, document):
        """ Returns ``True`` if the current document is somewhere in the
            path from :param:`document` to ``__root__``, else ``False``. """

        while document.parent is not None:
            if document.parent == self:
                return True

            document = document.parent

        return False


class PseudoQuerySet(list):
    """ Sometimes Django expects a queryset, but we build a complexly
        sorted list, and we want this list to display nicely in forms. """

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)

        super(PseudoQuerySet, self).__init__(*args, **kwargs)

    def all(self):
        return self

    def none(self):
        return PseudoQuerySet()

    def clone(self):
        new_pqs = PseudoQuerySet()
        new_pqs[:] = self[:]
        return new_pqs

    def get(self, *args, **kwargs):
        """ Fake a :meth:`get` method, the easy way. """

        result = self.model.objects.get(*args, **kwargs)

        if result in self:
            return result

        raise self.model.DoesNotExist(u'No {0} found with query {1}'.format(
                                      self.model.__class__.__name__, kwargs))

    def filter(self, *args, **kwargs):
        """ Fake a :meth:`filter` method, the easy way. """

        results = self.model.objects.filter(*args, **kwargs)

        new_pqs = PseudoQuerySet(model=self.model)

        new_pqs[:] = [res for res in results if res in self]

        return new_pqs
