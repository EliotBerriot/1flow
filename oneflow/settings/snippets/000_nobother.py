# -*- coding: utf-8 -*-
"""
    Copyright 2013 Olivier Cortès <oc@1flow.io>

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

import warnings

with warnings.catch_warnings():
    # These warnings are produced by external packages
    # that we use in 1flow. We have no time to fix them
    # ourselves, and their developers didn't update their
    # own code. BUMMER!

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import django.conf.urls.defaults # NOQA
    import django.utils.hashcompat # NOQA
    try:
        import jpype # NOQA

    except ImportError:
        # In case we import on a machine where there is no JVM,
        # because JVM is installed only on 'medium' workers. In
        # fact, the standard install is completely broken (we
        # need to create symlinks for it to work properly), and
        # we should avoid crashing here,
        pass
