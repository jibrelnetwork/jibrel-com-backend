from django import forms
from django.db import transaction

from django_banking.contrib.wire_transfer.api.validators.swift_code import is_valid_swift_code
from django_banking.contrib.wire_transfer.iban import (generate_iban_check_digits, valid_iban)
from django_banking.contrib.wire_transfer.models import ColdBankAccount, UserBankAccount
from django_banking.models import Account, Asset
from django_banking.models.accounts.enum import AccountType


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

    @transaction.atomic()
    def save(self, commit=True):
        data = self.clean()
        asset = Asset.objects.main_fiat_for_customer(self.instance.user)
        account = Account.objects.create(
            asset=asset, type=AccountType.TYPE_NORMAL, strict=False
        )
        user_account = UserBankAccount.objects.create(
            swift_code=data.get('swift_code'),
            bank_name=data.get('bank_name'),
            holder_name=data.get('holder_name'),
            iban_number=data.get('iban_number'),
            user=self.instance.user,
            account=account,
        )
        self.instance.add_payment(
            payment_account=ColdBankAccount.objects.for_customer(self.instance.user).account,
            user_account=user_account.account,
            amount=self.data['amount'],
        )
        return self.instance
