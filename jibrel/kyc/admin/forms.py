from django import forms
from django.db import transaction, models
from django.utils import timezone
from django_select2.forms import Select2Widget

from jibrel.core.common.helpers import lazy
from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission,
    KYCDocument
)


class BasicKYCSubmissionForm(forms.ModelForm):
    passport_document_file = forms.ImageField()
    proof_of_address_document_file = forms.ImageField()

    class Meta:
        widgets = {
            'profile': Select2Widget,
            'country': Select2Widget,
            'nationality': Select2Widget
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and 'profile' in self.fields:
            self.fields['profile'].disabled = True
        # Temporary solution
        if self.instance.pk:
            self.fields['passport_document_file'].disabled = True
            self.fields['proof_of_address_document_file'].disabled = True

    def get_initial_for_field(self, field, field_name):
        if field_name in self.override_fields:
            document = getattr(self.instance, self.override_fields[field_name], None)
            return document and document.file
        return super().get_initial_for_field(field, field_name)

    @lazy
    def override_fields(self):
        model = self._meta.model

        def override_fields_():
            for name, field in self.fields.items():
                model_field = name.rstrip('_file')
                if not hasattr(model, model_field):
                    continue
                if isinstance(field, forms.ImageField) and \
                    isinstance(model._meta.get_field(model_field), models.ForeignKey):
                    yield name, model_field
        return dict(override_fields_())

    @transaction.atomic
    def save(self, commit=True):
        super(BasicKYCSubmissionForm, self).save(commit=False)
        if not self.instance.pk:
            self.instance.transitioned_at = timezone.now()
            self.instance.status = BaseKYCSubmission.DRAFT
        if self.instance.is_draft:
            self.save_documents()
        return super(BasicKYCSubmissionForm, self).save(commit)

    def save_documents(self):
        for field_name, model_field_name in self.override_fields.items():
            file_obj = self.cleaned_data.get(field_name)
            if not file_obj:
                return
            document = KYCDocument.objects.create(
                profile=self.cleaned_data['profile'],
                file=file_obj
            )
            setattr(self.instance, model_field_name, document)


class RejectKYCSubmissionForm(forms.ModelForm):
    class Meta:
        model = IndividualKYCSubmission
        fields = ('reject_reason',)

    def clean_reject_reason(self):
        value = self.cleaned_data['reject_reason']
        if not value:
            raise forms.ValidationError('Provide reject reason')
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'reject_reason' in self.fields:
            self.fields['reject_reason'].required = True
