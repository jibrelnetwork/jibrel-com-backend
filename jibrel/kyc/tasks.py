import uuid
from io import BytesIO
from typing import Optional
from uuid import UUID

import requests
from celery import (
    Task,
    chain
)
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from onfido.rest import ApiException
from requests import (
    Response,
    codes
)

from jibrel.authentication.models import (
    Phone,
    User
)
from jibrel.celery import app
from jibrel.kyc.models import (
    BaseKYCSubmission,
    KYCDocument,
    PhoneVerification,
    PhoneVerificationCheck
)
from jibrel.kyc.onfido import check
from jibrel.kyc.onfido.api import OnfidoAPI
from jibrel.kyc.onfido.check import PersonalDocumentType
from jibrel.notifications.email import (
    KYCApprovedEmailMessage,
    KYCRejectedEmailMessage,
    KYCSubmittedEmailMessage,
    PhoneVerifiedEmailMessage
)
from jibrel.notifications.logging import LoggedCallTask
from jibrel.notifications.phone_verification import (
    PhoneVerificationChannel,
    TwilioVerifyAPI
)
from jibrel.notifications.tasks import send_mail

logger = get_task_logger(__name__)

twilio_verify_api = TwilioVerifyAPI(
    account_sid=settings.TWILIO_ACCOUNT_SID,
    secret_key=settings.TWILIO_AUTH_TOKEN,
    service_sid=settings.TWILIO_VERIFICATION_SERVICE_SID
)

onfido_api = OnfidoAPI(
    api_key=settings.ONFIDO_API_KEY,
    api_url=settings.ONFIDO_API_URL,
)


def get_task_id(task):
    return UUID(task.request.id)


@app.task(bind=True, base=LoggedCallTask)
def send_verification_code(
    self: LoggedCallTask,
    phone_uuid: str,
    channel: str,
    task_context: dict
) -> None:
    """Send PIN to phone via Twilio and store submission in PhoneVerification

    Args:
        self:
        phone_uuid:
        channel:
        task_context:

    Returns:
        CallLog with Twilio request submitted and response
    """
    phone = Phone.objects.get(uuid=phone_uuid)

    response = twilio_verify_api.send_verification_code(
        to=phone.number,
        channel=PhoneVerificationChannel(channel),
    )
    self.log_request_and_response(request_data=response.request.body, response_data=response.text)

    response.raise_for_status()
    data = response.json()

    with transaction.atomic():
        PhoneVerification.submit(
            sid=data['sid'],
            phone_id=UUID(phone_uuid),
            task_id=get_task_id(self),
            status=data['status']
        )
        phone.status = Phone.CODE_SENT
        phone.save()


@app.task(bind=True, base=LoggedCallTask, expires=settings.TWILIO_REQUEST_TIMEOUT)
def check_verification_code(
    self: LoggedCallTask,
    verification_id: str,
    pin: str,
    task_context: dict
) -> None:
    """Checks verification by sid and pin via Twilio and stores results in PhoneVerificationCheck

    Notes
        Updates PhoneVerification if check is not failed

    Args:
        self:
        verification_id:
        pin:
        task_context:

    Returns:
        CallLog with Twilio request submitted and response
    """
    verification = PhoneVerification.objects.get(pk=verification_id)
    response = twilio_verify_api.check_verification_code(
        verification_sid=verification.verification_sid,
        code=pin,
    )
    self.log_request_and_response(request_data=response.request.body, response_data=response.text)

    status = get_status_from_twilio_response(response)
    with transaction.atomic():
        check = PhoneVerificationCheck.objects.create(
            verification_id=verification_id,
            task_id=get_task_id(self),
            failed=status is None,
        )
        if status is None:
            logger.error('Twilio check failed: task_id %s', check.task_id)
            return

        check.set_status(status)

    if check.verification.phone.is_confirmed:
        send_phone_verified_email(
            task_context['user_id'],
            task_context['user_ip_address'],
        )


def get_status_from_twilio_response(response: Response) -> Optional[str]:
    if response.ok:
        return response.json()['status']
    if response.status_code == codes.too_many_requests:
        return PhoneVerification.MAX_ATTEMPTS_REACHED
    if response.status_code == codes.not_found:
        return PhoneVerification.EXPIRED
    return None


@app.task()
def enqueue_onfido_routine(submission: BaseKYCSubmission):
    person = check.Person.from_kyc_submission(submission)
    doc = person.documents[0]
    return chain(
        onfido_create_applicant_task.s(submission.account_type, submission.pk),
        onfido_upload_document_task.s(document_uuid=doc.uuid, document_type=doc.type.value,
                                      country=person.country),
        onfido_start_check_task.si(account_type=submission.account_type, kyc_submission_id=submission.pk),
        onfido_save_check_result_task.si(account_type=submission.account_type, kyc_submission_id=submission.pk),

    ).delay()


onfido_retry_options = dict(
    default_retry_delay=settings.ONFIDO_DEFAULT_RETRY_DELAY,
    max_retries=settings.ONFIDO_MAX_RETIES,
    retry_backoff=True,
    retry_jitter=True,
    retry_backoff_max=3600,
)


@app.task(bind=True, **onfido_retry_options)
def onfido_create_applicant_task(self: Task, account_type: str, kyc_submission_id: int):
    """Create applicant entity in OnFido for KYC submission `kyc_submission_id`"""

    logger.info('Started OnFido routine for Submission %s %s', account_type, kyc_submission_id)
    kyc_submission = BaseKYCSubmission.get_submission(account_type, kyc_submission_id)
    try:
        applicant_id = check.create_applicant(
            onfido_api,
            check.Person.from_kyc_submission(kyc_submission)
        )
    except ApiException as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    logger.info(f'Applicant successfully created in OnFido with ID {applicant_id}')
    kyc_submission.onfido_applicant_id = applicant_id
    kyc_submission.save()
    return applicant_id


@app.task(bind=True, **onfido_retry_options)
def onfido_upload_document_task(
    self: Task,
    applicant_id: str,
    *,
    document_uuid: uuid.UUID,
    document_type: str,
    country: str
):
    """Upload document `document_uuid` to OnFido for applicant `applicant_id`"""

    logger.info(f'Started uploading document {document_uuid} for applicant {applicant_id}')
    document = KYCDocument.objects.get(uuid=document_uuid)
    try:
        check.upload_document(
            onfido_api,
            applicant_id,
            check.PersonalDocument(
                uuid=document.pk,
                file=document.file,
                type=PersonalDocumentType(document_type),
                country=country
            )
        )
    except ApiException as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    logger.info(f'Document {document_uuid} for applicant {applicant_id} successfully uploaded')


@app.task(bind=True, **onfido_retry_options)
def onfido_start_check_task(self: Task, *, account_type: str, kyc_submission_id: int):
    """Initiate OnFido checking process by creating check entity in OnFido for submission `kyc_submission_id`"""

    kyc_submission = BaseKYCSubmission.get_submission(account_type, kyc_submission_id)
    logger.info(f'Started check creation for applicant {kyc_submission.onfido_applicant_id}')
    try:
        check_id = check.create_check(
            onfido_api,
            kyc_submission.onfido_applicant_id
        )
    except ApiException as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    logger.info(f'Check successfully for applicant {kyc_submission.onfido_applicant_id} with Check ID {check_id}')
    kyc_submission.onfido_check_id = check_id
    kyc_submission.save()


@app.task(
    bind=True,
    default_retry_delay=settings.ONFIDO_COLLECT_RESULTS_SCHEDULE,
    autoretry_for=(ApiException, requests.exceptions.HTTPError,),
    max_retries=settings.ONFIDO_MAX_RETIES,
)
def onfido_save_check_result_task(self, *, account_type: str, kyc_submission_id: int):
    """Save OnFido check results and report for submission `kyc_submission_id`"""

    kyc_submission = BaseKYCSubmission.get_submission(account_type, kyc_submission_id)
    result, report_url = check.get_check_result(
        onfido_api,
        kyc_submission.onfido_applicant_id,
        kyc_submission.onfido_check_id,
    )
    if not result:
        self.retry()
    report = check.download_report(
        onfido_api,
        report_url
    )
    kyc_submission.onfido_result = result
    kyc_submission.onfido_report.save(
        slugify(f'{kyc_submission.first_name} {kyc_submission.last_name}')
        + f' report {timezone.now().strftime("%Y_%m_%d_%H_%M_%S")}.pdf',
        File(BytesIO(report))
    ),
    kyc_submission.save()


@app.task()
def send_kyc_submitted_mail(account_type: str, kyc_submission_id: int):
    kyc_submission = BaseKYCSubmission.get_submission(account_type, kyc_submission_id)
    user = kyc_submission.profile.user
    rendered = KYCSubmittedEmailMessage.render({
        'name': user.profile.username,
        'email': user.email,
    }, language=user.profile.language)
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


@app.task()
def send_kyc_approved_mail(account_type: str, kyc_submission_id: int):
    kyc_submission = BaseKYCSubmission.get_submission(account_type, kyc_submission_id)
    user = kyc_submission.profile.user
    rendered = KYCApprovedEmailMessage.render({
        'name': user.profile.username,
        'email': user.email,
    }, language=user.profile.language)
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


@app.task()
def send_kyc_rejected_mail(account_type: str, kyc_submission_id: int):
    kyc_submission = BaseKYCSubmission.get_submission(account_type, kyc_submission_id)
    user = kyc_submission.profile.user
    rendered = KYCRejectedEmailMessage.render({
        'name': user.profile.username,
        'email': user.email,
        'reject_reason': kyc_submission.reject_reason,
    }, language=user.profile.language)
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


def send_phone_verified_email(user_id: str, user_ip: str):
    user = User.objects.get(pk=user_id)
    rendered = PhoneVerifiedEmailMessage.render({
        'name': user.profile.username,
        'phoneLastDigits': user.profile.phone.number[-4:],
        'email': user.email,
    }, language=user.profile.language)
    send_mail.delay(
        task_context={'user_id': user.uuid.hex, 'user_ip_address': user_ip},
        recipient=user.email,
        **rendered.serialize()
    )
