from django import forms
from django.db import (
    models,
    transaction
)
from django.utils import timezone
from django.utils.functional import cached_property
from django_select2.forms import Select2Widget, HeavySelect2Widget

from jibrel.kyc.models import (
    BaseKYCSubmission,
    Beneficiary,
    IndividualKYCSubmission,
    KYCDocument,
    OfficeAddress
)


class RelatedDocumentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and 'profile' in self.fields:
            self.fields['profile'].disabled = True
        # Temporary solution. see:
        # jibrel/kyc/admin/__init__.py:156
        if self.instance.pk and not self.instance.is_draft:
            for field_name in self.override_fields:
                self.fields[field_name].disabled = True

    def get_initial_for_field(self, field, field_name):
        if field_name in self.override_fields:
            document = getattr(self.instance, self.override_fields[field_name], None)
            return document and document.file
        return super().get_initial_for_field(field, field_name)

    @cached_property
    def override_fields(self):
        model = self._meta.model

        def override_fields_():
            for name, field in self.fields.items():
                model_field = name.rstrip('__file')
                if not hasattr(model, model_field):
                    continue
                if isinstance(field, forms.ImageField) and \
                    isinstance(model._meta.get_field(model_field), models.ForeignKey):
                    yield name, model_field
        return dict(override_fields_())

    @transaction.atomic
    def save(self, commit=True):
        super(RelatedDocumentForm, self).save(commit=False)
        if not self.instance.pk:
            self.instance.transitioned_at = timezone.now()
            self.instance.status = BaseKYCSubmission.DRAFT
        if self.instance.is_draft:
            self.save_documents()
        return super(RelatedDocumentForm, self).save(commit)

    @cached_property
    def profile(self):
        return self.cleaned_data['profile']

    def save_documents(self):
        for field_name, model_field_name in self.override_fields.items():
            file_obj = self.cleaned_data.get(field_name)
            if not file_obj:
                continue
            document = KYCDocument.objects.create(
                profile=self.profile,
                file=file_obj
            )
            setattr(self.instance, model_field_name, document)


class IndividualKYCSubmissionForm(RelatedDocumentForm):
    passport_document__file = forms.ImageField()
    proof_of_address_document__file = forms.ImageField()

    class Meta:
        widgets = {
            'profile': Select2Widget,
            'country': Select2Widget,
            'nationality': Select2Widget
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['account_type'].initial = BaseKYCSubmission.INDIVIDUAL
            self.fields['account_type'].disabled = True


class OrganizationKYCSubmissionForm(IndividualKYCSubmissionForm):
    commercial_register__file = forms.ImageField()
    shareholder_register__file = forms.ImageField()
    articles_of_incorporation__file = forms.ImageField()

    class Meta:
        widgets = {
            'profile': Select2Widget,
            'country': Select2Widget,
            'nationality': Select2Widget
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['account_type'].initial = BaseKYCSubmission.BUSINESS
            self.fields['account_type'].disabled = True


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


class OfficeAddressForm(forms.ModelForm):
    class Meta:
        model = OfficeAddress
        exclude = ('kyc_registered_here', 'kyc_principal_here')
        widgets = {
            'country': Select2Widget
        }


class BeneficiaryForm(RelatedDocumentForm):
    passport_document__file = forms.ImageField()
    proof_of_address_document__file = forms.ImageField()

    @cached_property
    def profile(self):
        return self.instance.organisational_submission.profile

    class Meta:
        model = Beneficiary
        fields = '__all__'
        exclude = ['passport_document', 'proof_of_address_document']
        widgets = {
            'country': HeavySelect2Widget(
                data_url='https://restcountries.eu/rest/v2/all'
            ),
            'nationality': HeavySelect2Widget(
                data_url='https://restcountries.eu/rest/v2/all'
            )
        }
