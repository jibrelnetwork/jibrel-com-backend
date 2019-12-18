import logging
from typing import Any

from celery.signals import before_task_publish
from celery.task import Task
from django.utils import timezone

from .models import ExternalServiceCallLog

sender_to_action = {
    'jibrel.kyc.tasks.send_verification_code': ExternalServiceCallLog.PHONE_VERIFICATION,
    'jibrel.kyc.tasks.check_verification_code': ExternalServiceCallLog.PHONE_CHECK_VERIFICATION,
    'jibrel.notifications.tasks.send_mail': ExternalServiceCallLog.SEND_MAIL,
}

logger = logging.getLogger()


@before_task_publish.connect
def celery_external_service_call_logger_start(sender: str, body: tuple, headers: dict, **kwargs: Any) -> None:
    """Signal handler for creating ExternalServiceCallLog instance before LoggedCallTask execution

    Extra context may be passed with `task_context` keyword argument into task function.
    Signal receiver waits `user_id` and `user_ip_address` parameters in the context.

    Notes
        You should explicitly define logged task in `sender_to_action` mapping.
        Signal executes in task caller process, not worker.

    Args:
        sender: task reference
        body: message body
        headers: message headers
        **kwargs:

    https://docs.celeryproject.org/en/latest/internals/protocol.html#message-protocol-task-v2
    """

    try:
        action_type = sender_to_action.get(sender)
        if action_type is None:
            return
        task_id = headers['id']
        _, kwargs, _ = body
        context = kwargs.get('task_context', {})
        initiator_type = context.get('initiator_type')
        if initiator_type is None:
            if context.get('user_id'):
                initiator_type = ExternalServiceCallLog.USER_INITIATOR
            elif context.get('user_ip_address'):
                initiator_type = ExternalServiceCallLog.ANON_INITIATOR
            else:
                initiator_type = ExternalServiceCallLog.SYSTEM_INITIATOR
        ExternalServiceCallLog.objects.create(
            uuid=task_id,
            action_type=action_type,
            initiator_type=initiator_type,
            initiator_id=context.get('user_id'),
            initiator_ip=context.get('user_ip_address'),
            kwargs=kwargs,
        )
    except Exception as exc:
        logger.exception(exc)
        raise exc


class LoggedCallTask(Task):
    """Task which can store data in previously created ExternalServiceCallLog model instance"""

    abstract = True

    def log_request_and_response(self, request_data: Any, response_data: Any,
                                 status: str = ExternalServiceCallLog.SUCCESS) -> None:
        log = ExternalServiceCallLog.objects.get(uuid=self.request.id)
        log.request_data = request_data
        log.response_data = response_data
        log.processed_at = timezone.now()
        log.status = status
        log.save()
