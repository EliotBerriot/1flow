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

from ....base.utils import connect_mongoengine_signals

#
# Make everything comfortly available to the outside.
#

from .common import * # NOQA
from .preferences  import * # NOQA

# user has to come before folder, subscription, read, feed
from .user import * # NOQA

# folder has to come before read, subscription
from .folder import * # NOQA

from .author import * # NOQA
from .website import * # NOQA
from .tag import * # NOQA

from .source import * # NOQA

# article needs source, website, author
from .article import * # NOQA

# feed needs article, read, user
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
