from django import forms
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError
)
from django.db.models import Q
from django_select2.forms import Select2Widget

from django_banking.models import Asset
from django_banking.models.assets.enum import AssetType
from jibrel.campaigns.enum import OfferingStatus
from jibrel.campaigns.models import (
    Offering,
    Security
)
from jibrel.core.forms.related_fields_form import RelatedFieldsForm


class SecurityForm(RelatedFieldsForm):
    asset__symbol = forms.CharField(
        max_length=Asset._meta.get_field('symbol').max_length,
        label=Asset._meta.get_field('symbol').verbose_name
    )

    class Meta:
        model = Security
        exclude = ['asset']
        widgets = {
            'company': Select2Widget(),
            'type': Select2Widget()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Temporary solution. see:
        # jibrel/kyc/admin/__init__.py:156
        if self.instance.asset_id and \
            'asset__symbol' in self.override_fields:
            self.fields['asset__symbol'].disabled = True

    def clean_asset__symbol(self):
        value = self.cleaned_data['asset__symbol']
        security_type = self.cleaned_data['type']
        company = self.cleaned_data['company']
        try:
            asset = Asset.objects.get(symbol=value)
            if asset.type not in AssetType.TOKEN:
                raise ValidationError(f'Asset with name {value} has incorrect type')

            if asset.security.type != security_type:
                raise ValidationError(f'Asset with name {value} has different security type')

        except ObjectDoesNotExist:
            # common shares by default. Otherwise it specified explicitly
            asset_name = company.name
            if self.instance == Security.TYPE_DEFAULT:
                asset_name += f', {self.instance.type}'

            asset = Asset.objects.create(
                type=AssetType.TOKEN,
                decimals=0,
                name=asset_name[:Asset._meta.get_field('name').max_length],
                symbol=value
            )

        return asset

    def save_related_fields(self):
        self.instance.asset = self.cleaned_data['asset__symbol']


class OfferingForm(forms.ModelForm):
    # please note:
    # ModelAdmin fieldset fields order is important to make clean process works

    class Meta:
        model = Offering
        fields = forms.ALL_FIELDS

    def clean_status(self):
        value = self.cleaned_data['status']

        if self.instance.status != value \
            and value not in Offering.STATUS_PIPELINE[self.instance.status]:
            raise ValidationError('Incorrect status')

        return value

    def clean_limit_max_amount(self):
        value = self.cleaned_data['limit_max_amount']
        limit_min_share = self.cleaned_data.get('limit_min_amount', 0)
        if value and value <= limit_min_share:
            raise ValidationError('Max allowed amount must be greater then minimum allowed amount to buy.')
        return value

    def clean_date_end(self):
        value = self.cleaned_data['date_end']
        date_start = self.instance.date_start or self.cleaned_data.get('date_start')
        if value <= date_start:
            raise ValidationError('Deadline must be greater then start date are.')

        security = self.cleaned_data.get('security')
        status = self.cleaned_data.get('status')
        if status == OfferingStatus.ACTIVE and \
            security and \
            Offering.objects.filter(
                Q(
                    date_start__lte=value,
                    date_end__gt=value,
                ) | Q(
                    date_start__lte=date_start,
                    date_end__gt=date_start,
                ),
                status=OfferingStatus.ACTIVE,
                security__company_id=security.company_id
            ).exclude(
                pk=self.instance.pk
            ).exists():
            raise ValidationError('There is another active campaign at the moment of time.')

        return value

    def clean_valuation(self):
        """
        Actually that case is possible. Probably it will be solved at the further releases.
        """
        value = self.cleaned_data['valuation']
        try:
            security = self.instance.security
        except ObjectDoesNotExist:
            security = self.cleaned_data.get('security')
        if security and Offering.objects.filter(
            security__company_id=security.company_id
        ).exclude(
            Q(valuation=value) | Q(pk=self.instance.pk)
        ).exists():
            raise ValidationError('Valuation must be same across all campaign rounds.')
        return value

    def clean_price(self):
        value = self.cleaned_data['price']
        goal = self.cleaned_data.get('goal')
        shares = self.cleaned_data.get('shares')

        if (shares and not value) or (value and not shares):
            raise ValidationError('Price cannot be defined if total shares amount not specified.')
        if value and shares and shares * value != goal:
            raise ValidationError('A product of price and shares must be equal to offering goal.')
        if value and shares and (value * 100) % 1 != 0:
            raise ValidationError('Too high precision. There only 2 decimal places is allowed.')
        return value

    def clean_goal(self):
        value = self.cleaned_data['goal']
        valuation = self.instance.valuation or self.cleaned_data.get('valuation')
        if valuation and valuation < value:
            raise ValidationError('Goal cannot be greater then total startup valuation.')
        return value
