from typing import Optional

from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models

from .queryset import (
    ProfileQuerySet,
    UserQuerySet
)


class UserManager(DjangoUserManager):
    def get_queryset(self):
        """
        Return a new QuerySet object. Subclasses can override this method to
        customize the behavior of the Manager.
        """
        return UserQuerySet(model=self.model, using=self._db, hints=self._hints)


class ProfileManager(models.Manager):  # type: ignore
    def get_basic_kyc_status(self, profile_id: int) -> Optional[str]:
        return self.with_last_basic_kyc_status().values_list(
            'last_kyc_status', flat=True
        ).get(pk=profile_id)

    def get_queryset(self):
        return ProfileQuerySet(model=self.model, using=self._db, hints=self._hints)

    def with_last_basic_kyc_status(self):
        return self.get_queryset().with_last_basic_kyc_status()
