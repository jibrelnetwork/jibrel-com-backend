from django import forms
from django.db import transaction
from django_select2.forms import Select2Widget

from django_banking.contrib.wire_transfer.api.validators.swift_code import (
    is_valid_swift_code
)
from django_banking.contrib.wire_transfer.iban import (
    generate_iban_check_digits,
    valid_iban
)
from django_banking.contrib.wire_transfer.models import (
    ColdBankAccount,
    UserBankAccount
)
from django_banking.models import (
    Account,
    Asset,
    UserAccount
)
from django_banking.models.accounts.enum import AccountType
from jibrel.investment.models import PersonalAgreement


class AddPaymentForm(forms.Form):
    swift_code = forms.CharField()
    bank_name = forms.CharField()
    holder_name = forms.CharField()
    iban_number = forms.CharField()
    amount = forms.DecimalField(min_value=0)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super(AddPaymentForm, self).__init__(*args, **kwargs)
        self.fields['amount'].widget.attrs.update({'value': self.instance.amount})

    def clean_iban_number(self):
        value = self.cleaned_data.get('iban_number')
        if not valid_iban(value) or generate_iban_check_digits(value) != value[2:4]:
            raise forms.ValidationError('Invalid IBAN')
        return value

    def clean_swift_code(self):
        value = self.cleaned_data.get('swift_code')
        if not is_valid_swift_code(value):
            raise forms.ValidationError('Invalid SWIFT')
        return value

    def clean(self):
        try:
            ColdBankAccount.objects.for_customer(self.instance.user).account
        except ColdBankAccount.DoesNotExist:
            raise forms.ValidationError('There is no USD cold bank account. It should be created first.')
        return super().clean()

    @transaction.atomic()
    def save(self, commit=True):
        """
        Temporary solution
        """
        data = self.clean()
        self.instance.amount = self.cleaned_data['amount']
        operation = self.instance.add_wire_transfer_deposit(
            **data,
            commit=False
        )
        try:
            operation.commit()
            self.instance.update_status(commit=False)
            self.instance.save(update_fields=('deposit', 'status', 'amount'))
        except Exception as exc:
            operation.cancel()
            raise exc
        return operation


class PersonalAgreementForm(forms.ModelForm):
    class Meta:
        model = PersonalAgreement
        fields = '__all__'
        widgets = {
            'offering': Select2Widget(),
            'user': Select2Widget()
        }
