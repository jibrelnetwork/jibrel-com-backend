import uuid
from io import BytesIO
from typing import Optional
from uuid import UUID

import phonenumbers
import requests
from django.conf import settings
from django.core.files import File
from django.utils import timezone
from django.utils.text import slugify
from onfido.rest import ApiException
from phonenumbers import PhoneNumber
from requests import Response, codes

from celery import Task, chain, group
from celery.utils.log import get_task_logger
from jibrel.authentication.models import Phone
from jibrel.celery import app
from jibrel.kyc.models import (
    BasicKYCSubmission,
    Document,
    PhoneVerification,
    PhoneVerificationCheck
)
from jibrel.kyc.onfido import check
from jibrel.kyc.onfido.api import OnfidoAPI
from jibrel.notifications.email import (
    KYCApprovedEmailMessage,
    KYCRejectedEmailMessage
)
from jibrel.notifications.logging import LoggedCallTask
from jibrel.notifications.phone_verification import (
    PhoneVerificationChannel,
    TwilioVerifyAPI
)
from jibrel.notifications.tasks import send_mail
# from jibrel.payments.limits import (
#     LimitInterval,
#     LimitType,
#     get_user_limits
# )

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
    code, number = Phone.objects.filter(uuid=phone_uuid).values_list('code', 'number').first()
    phone_number = phonenumbers.format_number(
        PhoneNumber(country_code=code, national_number=number),
        phonenumbers.PhoneNumberFormat.E164
    )

    response = twilio_verify_api.send_verification_code(
        to=phone_number,
        channel=PhoneVerificationChannel(channel),
    )
    self.log_request_and_response(request_data=response.request.body, response_data=response.text)

    if response.ok:
        data = response.json()

        PhoneVerification.submit(
            sid=data['sid'],
            phone_id=UUID(phone_uuid),
            task_id=UUID(self.request.id),
            status=data['status']
        )


@app.task(bind=True, base=LoggedCallTask, expires=settings.TWILIO_REQUEST_TIMEOUT)
def check_verification_code(
    self: LoggedCallTask,
    verification_sid: str,
    pin: str,
    task_context: dict
) -> bool:
    """Checks verification by sid and pin via Twilio and stores results in PhoneVerificationCheck

    Notes
        Updates PhoneVerification if check is not failed

    Args:
        self:
        verification_sid:
        pin:
        task_context:

    Returns:
        CallLog with Twilio request submitted and response
    """
    response = twilio_verify_api.check_verification_code(
        verification_sid=verification_sid,
        code=pin,
    )
    self.log_request_and_response(request_data=response.request.body, response_data=response.text)

    status = get_status_from_twilio_response(response)
    check = PhoneVerificationCheck.objects.create(
        verification_id=verification_sid,
        task_id=self.request.id,
        failed=status is None,
    )
    if status is not None:
        check.verification.status = status
        check.verification.save()

    return check.verification.status == PhoneVerification.APPROVED


def get_status_from_twilio_response(response: Response) -> Optional[str]:
    if response.ok:
        return response.json()['status']
    if response.status_code == codes.too_many_requests:
        return PhoneVerification.MAX_ATTEMPTS_REACHED
    return None


@app.task()
def enqueue_onfido_routine(basic_kyc_submission: BasicKYCSubmission = None, basic_kyc_submission_id: int = None):
    assert basic_kyc_submission or basic_kyc_submission_id
    if basic_kyc_submission is None:
        basic_kyc_submission = BasicKYCSubmission.objects.get(pk=basic_kyc_submission_id)
    person = check.Person(basic_kyc_submission)

    chain(
        onfido_create_applicant_task.s(basic_kyc_submission.id),
        group([
            onfido_upload_document_task.s(document_uuid=doc.uuid, country=person.country)
            for doc in person.documents
        ]),
        onfido_start_check_task.s(kyc_submission_id=basic_kyc_submission.id),
        onfido_save_check_result_task.si(kyc_submission_id=basic_kyc_submission.id),
    ).delay()


onfido_retry_options = dict(
    default_retry_delay=settings.ONFIDO_DEFAULT_RETRY_DELAY,
    max_retries=settings.ONFIDO_MAX_RETIES,
    retry_backoff=True,
    retry_jitter=True,
    retry_backoff_max=3600,
)


@app.task(bind=True, **onfido_retry_options)
def onfido_create_applicant_task(self: Task, kyc_submission_id: int):
    """Create applicant entity in OnFido for KYC submission `kyc_submission_id`"""

    logger.info(f'Started OnFido routine for Submission {kyc_submission_id}')
    kyc_submission = BasicKYCSubmission.objects.get(pk=kyc_submission_id)
    try:
        applicant_id = check.create_applicant(
            onfido_api,
            check.Person(kyc_submission)
        )
    except ApiException as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    logger.info(f'Applicant successfully created in OnFido with ID {applicant_id}')
    kyc_submission.onfido_applicant_id = applicant_id
    kyc_submission.save()
    return applicant_id


@app.task(bind=True, **onfido_retry_options)
def onfido_upload_document_task(self: Task, applicant_id: str, *_, document_uuid: uuid.UUID, country: str):
    """Upload document `document_uuid` to OnFido for applicant `applicant_id`"""

    logger.info(f'Started uploading document {document_uuid} for applicant {applicant_id}')
    document = Document.objects.get(uuid=document_uuid)
    try:
        check.upload_document(
            onfido_api,
            applicant_id,
            check.PersonalDocument(document, country)
        )
    except ApiException as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    logger.debug(f'Document {document_uuid} for applicant {applicant_id} successfully uploaded')


@app.task(bind=True, **onfido_retry_options)
def onfido_start_check_task(self: Task, *_, kyc_submission_id: int):
    """Initiate OnFido checking process by creating check entity in OnFido for submission `kyc_submission_id`"""

    kyc_submission = BasicKYCSubmission.objects.get(pk=kyc_submission_id)
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
def onfido_save_check_result_task(self, kyc_submission_id: int):
    """Save OnFido check results and report for submission `kyc_submission_id`"""

    kyc_submission = BasicKYCSubmission.objects.get(pk=kyc_submission_id)
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
def send_kyc_approved_mail(basic_kyc_submission_id: str):
    submission = BasicKYCSubmission.objects.get(pk=basic_kyc_submission_id)
    user = submission.profile.user
    # limits = get_user_limits(user)
    # limits_mapping = {(l.type, l.interval): l for l in limits}
    # deposit_limit = limits_mapping[(LimitType.DEPOSIT, LimitInterval.WEEK)]
    # withdrawal_limit = limits_mapping[(LimitType.WITHDRAWAL, LimitInterval.WEEK)]
    rendered = KYCApprovedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username,
        'sign_in_link': settings.APP_SIGN_IN_LINK.format(email=user.email),
        # 'limit': f'{deposit_limit.available}/{withdrawal_limit.available} {deposit_limit.asset.symbol}',
    })
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


@app.task()
def send_kyc_rejected_mail(basic_kyc_submission_id: str):
    submission = BasicKYCSubmission.objects.get(pk=basic_kyc_submission_id)
    user = submission.profile.user
    rendered = KYCRejectedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username,
        'sign_in_link': settings.APP_SIGN_IN_LINK.format(email=user.email),
        'reject_reason': submission.reject_reason,
    })
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )
