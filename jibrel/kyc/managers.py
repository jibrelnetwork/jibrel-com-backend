from django.db import models


class BasicKYCSubmissionManager(models.Manager):
    def approved_later_exists(self, submission) -> bool:
        from .models import BasicKYCSubmission
        assert isinstance(submission, BasicKYCSubmission)
        return not self.get_queryset().filter(
            profile=submission.profile,
            status=BasicKYCSubmission.APPROVED,
            created_at__gt=submission.created_at
        ).exists()
