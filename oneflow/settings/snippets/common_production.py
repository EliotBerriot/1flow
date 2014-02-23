# -*- coding: utf-8 -*-
#
# Put production machines hostnames here.
#
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

MANAGERS += (('Matthieu Chaignot', 'mchaignot@gmail.com'), )

EMAIL_SUBJECT_PREFIX='[1flow admin] '

ALLOWED_HOSTS += [
    '1flow.io',
    'app.1flow.io',
    'api.1flow.io',
]

