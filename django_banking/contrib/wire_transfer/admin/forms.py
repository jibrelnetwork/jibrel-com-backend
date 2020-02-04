from django import forms
from django.forms.utils import ErrorList

from django_banking.models import (
    Account,
    Asset
)
from django_banking.models.accounts.enum import AccountType
from django_banking.models.assets.enum import AssetType

from ..models import ColdBankAccount


class DepositBankAccountForm(forms.ModelForm):
    asset = forms.ModelChoiceField(
        queryset=Asset.objects.filter(type=AssetType.FIAT),
        help_text='Asset cannot be changed once created'
    )

    class Meta:
        model = ColdBankAccount
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
        asset = self.instance.account.asset if self.instance.account_id else cleaned_data.get('asset')
        if ColdBankAccount.objects.filter(
            account__asset=asset,
            is_active=True,
        ).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError(
                'Active deposit bank account with such fiat already exists'
            )

    def save(self, commit=True):
        asset = self.instance.account.asset if self.instance.account_id else self.cleaned_data.get('asset')
        print('1231231')
        account_data = {
            'asset': asset,
            'type': AccountType.TYPE_PASSIVE,
            'strict': True
        }

        account = Account.objects.create(**account_data)
        self.instance.account = account

        return super().save(commit=commit)
