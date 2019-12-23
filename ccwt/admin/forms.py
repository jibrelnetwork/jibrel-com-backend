from django import forms
from django.conf import settings
from django.forms.utils import ErrorList

from jibrel.accounting.models import (
    Account,
    Asset
)

from ccwt.settings import ACCOUNTING_MAX_DIGITS
from jibrel.authentication.models import User
from jibrel.payments.models import (
    DepositBankAccount,
    DepositCryptoAccount,
    DepositCryptoOperation
)


class DepositCryptoAccountForm(forms.ModelForm):
    asset = forms.ModelChoiceField(queryset=Asset.objects.all())
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)

    class Meta:
        model = DepositCryptoAccount
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
            'type': Account.TYPE_PASSIVE,
            'strict': True
        }

        account = Account.objects.create(**account_data)
        self.instance.account = account

        return super().save(commit=commit)


class DepositBankAccountForm(forms.ModelForm):
    asset = forms.ModelChoiceField(queryset=Asset.objects.all())

    class Meta:
        model = DepositBankAccount
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

    def clean(self):
        cleaned_data = super().clean()
        self._check_for_equal_accounts(cleaned_data)
        return cleaned_data

    def _check_for_equal_accounts(self, cleaned_data):
        """ Raise exception if there is another active DepositBankAccount with the same asset """
        if not cleaned_data.get('is_active'):
            return
        asset = cleaned_data.get('asset')
        if DepositBankAccount.objects.filter(
            account__asset=asset,
            is_active=True,
        ).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError(
                'Active deposit bank account with such fiat already exists'
            )

    def save(self, commit=True):
        asset = self.cleaned_data['asset']

        account_data = {
            'asset': asset,
            'type': Account.TYPE_PASSIVE,
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
            deposit_crypto_account = DepositCryptoAccount.objects.get(address=address)
        except DepositCryptoAccount.DoesNotExist:
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
