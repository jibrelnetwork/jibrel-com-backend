from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet


class PhoneInlineFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()

    def validate_unique(self):
        super().validate_unique()
        forms_to_delete = self.deleted_forms
        valid_forms = [form for form in self.forms if form.is_valid() and form not in forms_to_delete]
        is_primary = False
        for form in valid_forms:
            if is_primary and form.cleaned_data['is_primary']:
                raise ValidationError('There should be one and only primary phone')
            is_primary = form.cleaned_data['is_primary']
