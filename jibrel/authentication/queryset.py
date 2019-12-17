from django.db import models
from django.db.models import (
    OuterRef,
    Subquery,
    Value
)
from django.db.models.functions import (
    Concat,
    NullIf
)


class UserQuerySet(models.QuerySet):
    def with_full_name(self):
        return self.annotate(
            full_name=Concat(
                'profile__last_kyc__individual__last_name',
                Value(' '),
                'profile__last_kyc__individual__first_name',
                NullIf(
                    Concat(
                        Value(' '),
                        'profile__last_kyc__individual__middle_name',
                    ),
                    Value(' ')
                )
            )
        )

    def with_current_phone(self):
        from .models import Phone
        return self.annotate(
            current_phone=Subquery(
                Phone.objects.filter(
                    profile__user_id=OuterRef('pk')
                ).order_by(
                    '-created_at'
                ).values(
                    'number'
                )[:1],
                output_field=models.CharField()
            )
        )


class ProfileQuerySet(models.QuerySet):
    def with_last_basic_kyc_status(self):
        from jibrel.kyc.models import IndividualKYCSubmission
        return self.annotate(
            last_basic_kyc_status=Subquery(
                IndividualKYCSubmission.objects
                    .filter(profile_id=OuterRef('pk'))
                    .exclude(status=IndividualKYCSubmission.DRAFT)
                    .order_by('-created_at').values('status')[:1]
            )
        )
