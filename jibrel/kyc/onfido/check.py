import tempfile
from datetime import date
from enum import Enum
from typing import List, Optional
from uuid import UUID

import pycountry
from django.core.files import File

from ..models import BasicKYCSubmission, Document
from .api import OnfidoAPI


class PersonalDocumentType(Enum):
    NATIONAL_ID: str = 'national_identity_card'
    PASSPORT: str = 'passport'


class PersonalDocumentSide(Enum):
    FRONT: str = 'front'
    BACK: str = 'back'


class PersonalDocument:
    TYPE_MAPPING = {
        Document.NATIONAL_ID: PersonalDocumentType.NATIONAL_ID,
        Document.PASSPORT: PersonalDocumentType.PASSPORT
    }
    uuid: UUID
    file: File
    type: PersonalDocumentType
    side: PersonalDocumentSide
    country: str

    def __init__(self, document: Document, country: str):
        self.uuid = document.uuid
        self.file = document.file
        self.type = self.TYPE_MAPPING.get(document.type)
        self.side = PersonalDocumentSide(document.side)
        self.country = _to_alpha_3(country)


class Person:
    full_name: str
    email: str
    birth_date: date
    country: str
    documents: List[PersonalDocument]

    def __init__(self, kyc_submission: BasicKYCSubmission):
        self.first_name = kyc_submission.data['firstName']
        self.middle_name = kyc_submission.data['middleName']
        self.last_name = kyc_submission.data['lastName']
        self.email = kyc_submission.profile.user.email
        self.birth_date = kyc_submission.data['birthDate']
        self.country = _to_alpha_3(kyc_submission.data['country'])
        self._build_documents(kyc_submission)

    def _build_documents(self, kyc_submission: BasicKYCSubmission):
        self.documents = [
            PersonalDocument(kyc_submission.data['personalIdDocumentFront'], kyc_submission.data['nationality']),
        ]
        if kyc_submission.data['personalIdType'] == Document.NATIONAL_ID:
            self.documents.append(
                PersonalDocument(kyc_submission.data['personalIdDocumentBack'], kyc_submission.data['nationality']),
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
            document_side=document.side.value,
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
