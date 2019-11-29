from datetime import timedelta

from django.db import models
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Cast
from django.utils import timezone
from django.contrib.postgres.fields.jsonb import KeyTextTransform, KeyTransform


class PhoneVerificationQuerySet(models.QuerySet):
    def failed(self) -> 'PhoneVerificationQuerySet':
        from .models import PhoneVerification
        return self.exclude(status=PhoneVerification.APPROVED)

    def created_in_last(self, seconds: int) -> 'PhoneVerificationQuerySet':
        return self.filter(
            created_at__gte=timezone.now() - timedelta(seconds=seconds)
        )

    def pending(self) -> 'PhoneVerificationQuerySet':
        from .models import PhoneVerification
        return self.filter(status=PhoneVerification.PENDING)

    def throttled(self) -> 'PhoneVerificationQuerySet':
        from .models import PhoneVerification
        return self.filter(status=PhoneVerification.MAX_ATTEMPTS_REACHED)


class DocumentQuerySet(models.QuerySet):
    def not_used_in_basic_kyc(self):
        from .models import BasicKYCSubmission
        return self.annotate(

            uuid_str=Cast('uuid', output_field=models.CharField()),
            used_in_basic_kyc=Exists(
                BasicKYCSubmission.objects.annotate(
                    personalIdDocumentFront=KeyTextTransform('data', 'data__personalIdDocumentFront'),
                    personalIdDocumentBack=KeyTextTransform('data', 'data__personalIdDocumentBack'),
                    proofOfAddress=KeyTextTransform('proofOfAddress', 'data__proofOfAddress')
                ).filter(
                    Q(personalIdDocumentFront=OuterRef('uuid_str')) |
                    Q(personalIdDocumentBack=OuterRef('uuid_str')) |
                    Q(proofOfAddress=OuterRef('uuid_str'))
                )
            )
        ).filter(used_in_basic_kyc=False)
