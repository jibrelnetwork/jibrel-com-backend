import tempfile
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import (
    List,
    Optional
)
from uuid import UUID

import pycountry
from django.core.files import File

from jibrel.kyc.models import BaseKYCSubmission

from .api import OnfidoAPI


class PersonalDocumentType(Enum):
    NATIONAL_ID: str = 'national_identity_card'
    PASSPORT: str = 'passport'
    UNKNOWN: str = 'unknown'


@dataclass
class PersonalDocument:
    uuid: UUID
    file: File
    type: PersonalDocumentType
    country: str


@dataclass
class Person:
    first_name: str
    middle_name: Optional[str]
    last_name: str
    email: str
    birth_date: date
    country: str
    documents: List[PersonalDocument]

    @classmethod
    def from_kyc_submission(cls,  submission: BaseKYCSubmission) -> 'Person':
        if submission.account_type == BaseKYCSubmission.INDIVIDUAL:
            email = submission.profile.user.email
        else:
            email = submission.email
        return Person(
            first_name=submission.first_name,
            middle_name=submission.middle_name,
            last_name=submission.last_name,
            email=email,
            birth_date=submission.birth_date,
            country=_to_alpha_3(submission.country),
            documents=[
                PersonalDocument(
                    uuid=submission.passport_document.pk,
                    file=submission.passport_document.file,
                    type=PersonalDocumentType.PASSPORT,
                    country=submission.country,
                ),
                PersonalDocument(
                    uuid=submission.proof_of_address_document.pk,
                    file=submission.proof_of_address_document.file,
                    type=PersonalDocumentType.UNKNOWN,
                    country=submission.country,
                ),
            ]
        )


def _to_alpha_3(country: str):
    if len(country) == 3:
        return country
    return pycountry.countries.get(alpha_2=country.upper()).alpha_3


def create_applicant(onfido_api: OnfidoAPI, person: Person) -> str:
    applicant_id = onfido_api.create_applicant(
        first_name=person.first_name,
        last_name=person.last_name,
        email=person.email,
        birth_date=person.birth_date,
        country=person.country,
        middle_name=person.middle_name,
    )
    return applicant_id


def upload_document(onfido_api: OnfidoAPI, applicant_id: str, document: PersonalDocument):
    with tempfile.NamedTemporaryFile(suffix=document.file.name) as f:
        f.write(document.file.read())
        f.seek(0)

        onfido_api.upload_document(
            applicant_id=applicant_id,
            file_path=f.name,
            document_type=document.type.value,
            country=document.country,
        )


def create_check(onfido_api: OnfidoAPI, applicant_id: str) -> str:
    return onfido_api.create_check(
        applicant_id=applicant_id,
    )


ONFIDO_STATUS_COMPLETE = 'complete'


def get_check_result(onfido_api: OnfidoAPI, applicant_id: str, check_id: str):
    check_result = onfido_api.get_check_results(
        applicant_id=applicant_id,
        check_id=check_id,
    )
    if check_result.status != ONFIDO_STATUS_COMPLETE:
        return None, None
    return check_result.result, f'{check_result.download_uri}.pdf'


def download_report(onfido_api: OnfidoAPI, report_url: str) -> bytes:
    return onfido_api.download_report(report_url)
