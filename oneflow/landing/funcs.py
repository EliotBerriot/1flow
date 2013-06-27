
import datetime

from django.conf import settings

from models import LandingContent, LandingUser


def get_all_beta_data():
    """ Return all Landing BETA related data, in a way suited to be used as::

        context.update(get_all_beta_data())

    """

    return get_translations() + get_beta_invites_left() + get_beta_time_left()


def get_beta_invites_left(only_number=False):

    beta_invites_left = settings.LANDING_BETA_INVITES \
        - LandingUser.objects.count()

    if only_number:
        return beta_invites_left

    return (('beta_invites_left', beta_invites_left), )


def get_beta_time_left():

    delta = (settings.LANDING_BETA_DATE - datetime.datetime.now())

    return (('beta_time_left', delta.days * 86400 + delta.seconds), )


def get_translations():

    # We can't speed up this thing with .values_list() because
    # Transmeta's way of doing thing isn't compatible with it:
    # it would need to specify the *_lang field name, which
    # would avoid the ability to fallback to default lang if
    # the field has no translation.
    return tuple((x.name, x.content) for x in LandingContent.objects.all())
