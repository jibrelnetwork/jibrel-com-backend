from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.db import transaction
from django.utils import timezone
from django_json_widget.widgets import JSONEditorWidget

from jibrel.kyc.models import BasicKYCSubmission, Document


class BasicKYCSubmissionForm(forms.ModelForm):
    class Meta:
        model = BasicKYCSubmission

        fields = '__all__'

        widgets = {
            # choose one mode from ['text', 'code', 'tree', 'form', 'view']
            'data': JSONEditorWidget(mode='view')
        }


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
