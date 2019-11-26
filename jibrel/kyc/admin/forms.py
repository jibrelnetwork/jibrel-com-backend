from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.db import transaction
from django.utils import timezone

from jibrel.kyc.models import BasicKYCSubmission, Document


class BasicKYCSubmissionForm(forms.ModelForm):
    personal_id_document_front_file = forms.ImageField()
    personal_id_document_back_file = forms.ImageField(required=False)
    residency_visa_document_file = forms.ImageField(required=False)
    residency_visa_number = forms.CharField(required=False)
    residency_visa_doe = forms.DateField(required=False, widget=AdminDateWidget())

    form_to_model_document_fields = {
        'personal_id_document_front_file': 'personal_id_document_front',
        'personal_id_document_back_file': 'personal_id_document_back',
        'residency_visa_document_file': 'residency_visa_document',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and 'profile' in self.fields:
            self.fields['profile'].disabled = True

    def get_initial_for_field(self, field, field_name):
        if field_name in self.form_to_model_document_fields:
            model_field = self.form_to_model_document_fields[field_name]
            document = getattr(self.instance, model_field, None)
            return document and document.file
        return super().get_initial_for_field(field, field_name)

    @transaction.atomic
    def save(self, commit=True):
        super(BasicKYCSubmissionForm, self).save(commit=False)
        self.save_personal_id_document_front_file()
        self.save_personal_id_document_back_file()
        self.save_residency_visa_document_file()
        if not self.instance.pk:
            self.instance.transitioned_at = timezone.now()
            self.instance.status = BasicKYCSubmission.DRAFT
        return super(BasicKYCSubmissionForm, self).save(commit)

    def save_personal_id_document_front_file(self):
        if 'personal_id_document_front_file' not in self.changed_data:
            return
        document_type = Document.PASSPORT if self.cleaned_data['citizenship'] in \
            BasicKYCSubmission.SUPPORTED_COUNTRIES else Document.NATIONAL_ID
        self.instance.personal_id_document_front = self._save_document_field(
            field_name='personal_id_document_front_file',
            side='front',
            document_type=document_type
        )

    def save_personal_id_document_back_file(self):
        if 'personal_id_document_back_file' not in self.changed_data:
            return
        document_type = Document.PASSPORT if self.cleaned_data['citizenship'] in \
            BasicKYCSubmission.SUPPORTED_COUNTRIES else Document.NATIONAL_ID
        self.instance.personal_id_document_back = self._save_document_field(
            field_name='personal_id_document_back_file',
            side='back',
            document_type=document_type
        )

    def save_residency_visa_document_file(self):
        if 'residency_visa_document_file' not in self.changed_data:
            return
        self.instance.residency_visa_document = self._save_document_field(
            field_name='residency_visa_document_file',
            side='front',
            document_type=Document.RESIDENCY_VISA,
        )

    def _save_document_field(self, field_name, side, document_type):
        file_obj = self.cleaned_data.get(field_name)
        if not file_obj:
            return
        return Document.objects.create(
            profile=self.cleaned_data['profile'],
            file=file_obj,
            side=side,
            type=document_type,
        )


class RejectKYCSubmissionForm(forms.ModelForm):
    class Meta:
        model = BasicKYCSubmission
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
