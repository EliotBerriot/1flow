# -*- coding: utf-8 -*-

from ....base.utils import connect_mongoengine_signals

#
# Make everything comfortly available to the outside.
#

from .common import * # NOQA
from .preferences  import * # NOQA

# user has to come before folder, subscription, read
from .user import * # NOQA

# folder has to come before read, subscription
from .folder import * # NOQA

from .author import * # NOQA
from .website import * # NOQA
from .tag import * # NOQA

from .source import * # NOQA

# article needs source, website, author
from .article import * # NOQA

# feed needs article, read
from .feed import * # NOQA

# subscription needs folder, user, feed
from .subscription import * # NOQA

# read needs article, folder, subscription, user
from .read import * # NOQA

# We need to explicitely clutter the class globals for it
# to find the *_replace_duplicate_everywhere celery tasks.
DocumentHelperMixin.nonrel_globals = globals()

# Now that everything is imported, connect all
# classmethod handlers to MongoEngine signals.
connect_mongoengine_signals(globals())
