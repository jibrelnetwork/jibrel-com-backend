from django.db import models
from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Concat, NullIf


class UserQuerySet(models.QuerySet):
    def with_full_name(self):
        return self.annotate(
            full_name=Concat(
                'profile__last_basic_kyc__last_name',
                Value(' '),
                'profile__last_basic_kyc__first_name',
                NullIf(
                    Concat(
                        Value(' '),
                        'profile__last_basic_kyc__middle_name',
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
                ).annotate(
                    full_number=Concat('code', 'number')
                ).order_by(
                    '-created_at'
                ).values(
                    'full_number'
                )[:1],
                output_field=models.CharField()
            )
        )


class ProfileQuerySet(models.QuerySet):
    def with_last_basic_kyc_status(self):
        from jibrel.kyc.models import BasicKYCSubmission
        return self.annotate(
            last_basic_kyc_status=Subquery(
                BasicKYCSubmission.objects
                    .filter(profile_id=OuterRef('pk'))
                    .exclude(status=BasicKYCSubmission.DRAFT)
                    .order_by('-created_at').values('status')[:1]
            )
        )
