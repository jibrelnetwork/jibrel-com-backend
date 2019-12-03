from dataclasses import dataclass
from datetime import date
from typing import Optional

import onfido
import requests


@dataclass
class CheckResult:
    status: str
    result: str
    download_uri: str


class OnfidoAPI:
    def __init__(
        self,
        api_key: str,
        api_url: str,
    ):
        configuration = onfido.Configuration()
        configuration.host = api_url
        self.api = onfido.DefaultApi(
            onfido.ApiClient(
                configuration=configuration,
                header_name='Authorization',
                header_value=f'Token token={api_key}'
            )
        )

    def create_applicant(
        self,
        first_name: str,
        last_name: str,
        email: str,
        birth_date: date,
        country: str,
        middle_name: Optional[str] = None,
    ) -> str:
        response = self.api.create_applicant(
            onfido.Applicant(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                email=email,
                dob=birth_date,
                country=country,
            )
        )
        return response.id

    def upload_document(
        self,
        applicant_id: str,
        file_path: str,
        document_type: str,
        document_side: str,
        country: str,
    ) -> str:
        response = self.api.upload_document(
            applicant_id=applicant_id,
            file=file_path,
            type=document_type,
            side=document_side,
            issuing_country=country,
        )
        return response.id

    def create_check(
        self,
        applicant_id: str,
    ):
        reports = [
            onfido.Report(name='document'),
            onfido.Report(name='watchlist', variant='full'),
        ]
        check = onfido.Check(
            type='express',
            reports=reports
        )
        response = self.api.create_check(applicant_id, check)
        return response.id

    def get_check_results(
        self,
        applicant_id: str,
        check_id: str
    ) -> CheckResult:
        response = self.api.find_check(
            applicant_id,
            check_id,
        )
        return CheckResult(
            response.status,
            response.result,
            response.download_uri,
        )

    def download_report(self, url: str) -> bytes:
        response = requests.get(
            url,
            headers=self.api.api_client.default_headers,
        )
        response.raise_for_status()
        return response.content
