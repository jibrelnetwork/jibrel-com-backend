from datetime import timedelta

from django.db import models
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone


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
    def not_used_in_kyc(self):
        from .models import IndividualKYCSubmission
        return self.annotate(
            used_in_individual_kyc=Exists(
                IndividualKYCSubmission.objects.filter(
                    Q(passport_document_id=OuterRef('uuid')) |
                    Q(proof_of_address_document_id=OuterRef('uuid'))
                )
            )
        ).filter(used_in_individual_kyc=False)
