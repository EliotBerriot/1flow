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

from social_auth.backends.facebook import FacebookBackend
from social_auth.backends.twitter import TwitterBackend
from social_auth.backends import google


LOGGER = logging.getLogger(__name__)


def get_social_avatar(social_user, user, details, request, response, backend,
                      is_new=False, *args, **kwargs):

    try:
        url = None

        if isinstance(backend, FacebookBackend):
            if 'id' in response:
                url = 'http://graph.facebook.com/%s/picture?type=large' \
                            % response['id']

        elif isinstance(backend, google.GoogleOAuth2Backend):
            url = response.get('picture', None)

        elif isinstance(backend, TwitterBackend):
            url = response.get('profile_image_url', None)

        if url:
            mongo_user = user.mongo

            if mongo_user.avatar_url != url:
                mongo_user.avatar_url = url
                mongo_user.save()

                LOGGER.info(u'Saved new avatar for user %s from backend %s.',
                            user, social_user)

        #     avatar = urlopen(url)
        #     photo = Photo(author=user, is_avatar=True)
        #     photo.picture.save(slugify(user.username+"social") + '.jpg',
        #             ContentFile(avatar.read()))
        #     photo.save()

    except:
        LOGGER.exception(u'Could not get avatar for user %s from '
                         u'backend %s.', user, social_user)
