from django import forms
from django.forms.utils import ErrorList

from django_banking.models import (
    Account,
    Asset
)
from django_banking.models.accounts.enum import AccountType
from django_banking.user import User
from django_banking.settings import (
    ACCOUNTING_DECIMAL_PLACES,
    ACCOUNTING_MAX_DIGITS
)

from ..models import (
    UserCryptoDepositAccount,
    DepositCryptoOperation
)


class DepositCryptoAccountForm(forms.ModelForm):
    asset = forms.ModelChoiceField(queryset=Asset.objects.all())
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)

    class Meta:
        model = UserCryptoDepositAccount
        exclude = ['account']

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=None,
                 empty_permitted=False, instance=None, use_required_attribute=None,
                 renderer=None):
        if instance is not None:
            initial = initial or {}
            initial['asset'] = instance.account.asset
        super().__init__(
            data, files, auto_id, prefix, initial, error_class, label_suffix,
            empty_permitted, instance, use_required_attribute, renderer,
        )

    def save(self, commit=True):
        asset = self.cleaned_data['asset']

        account_data = {
            'asset': asset,
            'type': AccountType.TYPE_PASSIVE,
            'strict': True
        }

        account = Account.objects.create(**account_data)
        self.instance.account = account

        return super().save(commit=commit)


class DepositCryptoOperationForm(forms.ModelForm):
    address = forms.CharField()
    amount = forms.DecimalField(
        max_digits=ACCOUNTING_MAX_DIGITS, decimal_places=ACCOUNTING_DECIMAL_PLACES
    )
    tx_hash = forms.CharField(label='TX hash', max_length=255)

    def clean_address(self):
        address = self.cleaned_data['address']
        try:
            deposit_crypto_account = UserCryptoDepositAccount.objects.get(address=address)
        except UserCryptoDepositAccount.DoesNotExist:
            raise forms.ValidationError('Account with that address doesn\'t exist')
        if deposit_crypto_account.user_id is None:
            raise forms.ValidationError('Account with that address hasn\'t assigned to any user')
        self.cleaned_data['deposit_crypto_account'] = deposit_crypto_account
        return address

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount should be bigger than 0')
        return amount

    def save(self, commit=True):
        operation = DepositCryptoOperation.objects.create_deposit(
            deposit_crypto_account=self.cleaned_data['deposit_crypto_account'],
            amount=self.cleaned_data['amount'],
            metadata={'tx_hash': self.cleaned_data['tx_hash']}
        )

        return operation

    def save_m2m(self):
        pass  # ModelAdmin try to call this method, but we fully overrode default behaviour of save method


class WithdrawalCryptoOperationForm(forms.ModelForm):
    tx_hash = forms.CharField(label='TX hash', max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['tx_hash'] = self.instance.metadata.get('tx_hash')

    def save(self, commit=True):
        self.instance.metadata['tx_hash'] = self.cleaned_data['tx_hash']
        return super().save(commit)

    def save_m2m(self):
        pass  # ModelAdmin try to call this method, but we fully overrode default behaviour of save method
