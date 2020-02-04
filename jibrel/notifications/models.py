from datetime import timedelta
from uuid import (
    UUID,
    uuid4
)

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property


class ExternalServiceCallLog(models.Model):
    """External service call logging model
    Allows keep all data ever been called from external resources.

    Assuming that every call would be processed through this model we can guarantee
    to whole data sent or received from our service would be logged and kept in database.
    """
    # action types
    PHONE_VERIFICATION = 1
    PHONE_CHECK_VERIFICATION = 2
    SEND_MAIL = 3

    ACTION_TYPES = (
        (PHONE_VERIFICATION, 'Phone verification code sending'),
        (PHONE_CHECK_VERIFICATION, 'Phone verification code checking'),
        (SEND_MAIL, 'Send mail'),
    )

    # initiator types
    USER_INITIATOR = 'user'
    ANON_INITIATOR = 'anonymous'
    SYSTEM_INITIATOR = 'system'

    INITIATOR_TYPES = (
        (USER_INITIATOR, 'User'),
        (ANON_INITIATOR, 'Anonymous user'),
        (SYSTEM_INITIATOR, 'System'),
    )

    SUCCESS = 'success'
    ERROR = 'error'
    STATUS = (
        (SUCCESS, 'Success'),
        (ERROR, 'Error'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4)
    initiator_type = models.CharField(choices=INITIATOR_TYPES, max_length=20)
    initiator = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT, null=True)
    initiator_ip = models.GenericIPAddressField(null=True)
    action_type = models.IntegerField(choices=ACTION_TYPES)
    kwargs = JSONField()
    request_data = JSONField(null=True)
    response_data = JSONField(null=True)

    processed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=32,
        choices=STATUS,
        default=SUCCESS
    )

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def was_request_in(cls, initiator_id: UUID, action_type: int, seconds_ago: int) -> bool:
        """Check any instance of ExternalServiceCallLog model initiated by `initiator_id`
        with action type `action_type` exists in time period from (now - `seconds_ago`) to now
        """
        return cls.objects.filter(
            initiator_id=initiator_id,
            action_type=action_type,
            created_at__gte=timezone.now() - timedelta(seconds=seconds_ago)
        ).exists()

    def __str__(self):
        return ', '.join(map(str, filter(bool, (
            self.initiator_type,
            self.initiator,
            self.initiator_ip
        ))))

    @cached_property
    def success(self):
        return self.status == self.SUCCESS
