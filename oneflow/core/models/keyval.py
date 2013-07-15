# -*- coding: utf-8 -*-

import redis

from django.db import models
from mongoengine import EmbeddedDocument, fields
from django.conf import settings
from django.contrib.auth.models import User
#from django.utils.translation import ugettext as _

from .fields import ListField

REDIS = redis.StrictRedis(host=settings.REDIS_FEEDBACK_HOST,
                          port=settings.REDIS_FEEDBACK_PORT,
                          db=settings.REDIS_FEEDBACK_DB)


class RedisFeedbackMixin(object):
    """ Feddback machine, stored in Redis for fastiness.

        Implemented via 3 redis objects for every feedbacked instance:
            - an integer, the current score
            - a list of users who +ed the instance
            - a list of users who -ed the instance

        Only users IDs are stored in lists. The score and IDs will be
        Stored in the instance from time to time, for persistence. But
        In normal operations, only the REDIS backend gets hit.
    """

    def feedback_store_persistent(self):
        """ Meant to be run via a celery task, once a day or the like.
            Named after `*_persistent` to avoid confusion between
            `store` and `score`.
        """

        self.stored_feedback_score = self.score
        self.stored_feedback_positives, self.stored_feedback_negatives = \
            self.feedback_get()
        self.save()

    @property
    def feedback_key_base(self):
        return 'f:{0}:{1}'.format(self.__class__.__name__, self.id)

    @property
    def feedback_score(self):

        score = REDIS.get(self.feedback_key_base)

        if score is None:
            new_score = self.stored_feedback_score

            REDIS.set(score, new_score)

        return score

    def feedback_get(self, positive=None, resolve=False):
        """ Return either one or two lists of the Users (if :param:`resolve`
            is ``True``) or just their IDs.

            :param positive: a boolean indicating if you want the user who
                provided positive or negative feedback on the current
                instance. Can be ``None`` (which is the default), in which
                case 2 lists are returned ``(positive, negative)``.
            :param resolve: a boolean defaulting to ``False``. If ``True``,
                returned  lists will
                contain :class:`~django.contrib.auth.models.User`
                instances, else only plain integer IDs will be returned.

        """

        score_key = self.feedback_key_base

        if positive is None:
            pipe = REDIS.pipeline()

            positive_list, negative_list = (
                pipe.smembers(score_key + '+').smembers(
                    score_key + '-').execute()
            )

            if resolve:
                return (User.objects.filter(id__in=positive_list),
                        User.objects.filter(id__in=negative_list))

            return positive_list, negative_list

        else:
            ids = REDIS.smembers(score_key + '+' if positive else '-')

            if resolve:
                return User.objects.filter(id__in=ids)

            return ids

    def feedback_add(self, user, positive):

        score_key     = self.feedback_key_base
        feedback_list = score_key + '+' if positive else '-'
        feedback_neg  = score_key + '-' if positive else '+'

        if not REDIS.sadd(feedback_list, user.id):
            raise ValueError('Duplicate feedback for '
                             'user {0} on {1} #{2}'.format(
                             user, self.__class__.__name__, self.id))

        pipe = REDIS.pipeline()

        if positive:
            pipe.incr(score_key)

        else:
            pipe.decr(score_key)

        pipe.srem(feedback_neg, user.id)
        pipe.sadd(feedback_list, user.id)

        pipe.execute()


class RelationalFeedback(models.Model):
    """ Adds the feedback abilitily to any DB object."""

    stored_feedback_score     = models.IntegerField(default=0)
    stored_feedback_positives = ListField(default=[])
    stored_feedback_negatives = ListField(default=[])

    class Meta:
        abstract = True


class FeedbackDocument(EmbeddedDocument, RedisFeedbackMixin):
    """ Adds the feedback abilitily to any MongoEngine Document. """

    stored_feedback_score     = fields.IntField(default=0)
    stored_feedback_positives = fields.ListField()
    stored_feedback_negatives = fields.ListField()
