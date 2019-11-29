import importlib
from ..models import (
    BasicKYCSubmission
)


PERSONAL_SCHEMA_VERSION = 'v1'
BUSINESS_SCHEMA_VERSION = 'v1'


def get_kyc_version(kind: str, schema: str = None):
    """
    get form according to represented schema version
    :param kind:
    :param schema:
    :return:
    """
    kind = kind or BasicKYCSubmission.PERSONAL
    schema = schema or (PERSONAL_SCHEMA_VERSION if kind == BasicKYCSubmission.PERSONAL else BUSINESS_SCHEMA_VERSION)
    module = importlib.import_module(f'jibrel.kyc.schema.{kind.lower()}.{schema}')
    return module.SCHEMA


LatestPersonalBasicKYCSubmissionSchema = get_kyc_version(BasicKYCSubmission.PERSONAL, PERSONAL_SCHEMA_VERSION)
LatestBusinessBasicKYCSubmissionSchema = get_kyc_version(BasicKYCSubmission.BUSINESS, BUSINESS_SCHEMA_VERSION)
