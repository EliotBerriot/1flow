# -*- coding: utf-8 -*-

import logging

from constance import config

from django.shortcuts import redirect

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


def throttle_new_user_accounts(social_user, user, details, request,
                               response, backend, is_new=False,
                               *args, **kwargs):

    if is_new and not config.SOCIAL_REGISTRATION_ENABLED:

        user.is_active = False
        user.save()

        LOGGER.warning(u'De-activated new user account %s from backend %s on '
                       u'the fly because social registrations are currently '
                       u'disabled.', user, social_user)

        # Wrap the 'official' account view to signify the user we are closed.
        return redirect('signin_error')
