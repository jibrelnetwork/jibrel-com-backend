from typing import (
    Callable,
    Dict
)
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import (
    models,
    transaction
)
from django.db.models import (
    Q,
    UniqueConstraint
)
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_banking.contrib.wire_transfer.models import (
    ColdBankAccount,
    UserBankAccount
)
from django_banking.core.db.decorators import annotated
from django_banking.models import (
    Account,
    Asset,
    Operation,
    UserAccount
)
from django_banking.models.accounts.enum import AccountType
from django_banking.models.transactions.enum import (
    OperationMethod,
    OperationStatus
)
from django_banking.utils import generate_deposit_reference_code
from jibrel.campaigns.models import Offering

from ..core.common.rounding import rounded  # noqa
from ..payments.tasks import card_charge_request
from .enum import (
    InvestmentApplicationAgreementStatus,
    InvestmentApplicationStatus,
    SubscriptionAgreementEnvelopeStatus
)
from .managers import (
    InvestmentApplicationManager,
    InvestmentSubscriptionManager
)
from .storages import personal_agreements_file_storage


class InvestmentSubscription(models.Model):
    objects = InvestmentSubscriptionManager()
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT, related_name='subscribes')
    offering = models.ForeignKey(Offering, on_delete=models.CASCADE, related_name='subscribes')
    email = models.EmailField()
    amount = models.CharField(
        max_length=30,
        choices=(
            ('USD 1,000 - 9,999', 'USD 1,000 - 9,999'),
            ('USD 10,000 - 19,999', 'USD 10,000 - 19,999'),
            ('USD 20,000 - 49,999', 'USD 20,000 - 49,999'),
            ('USD 50,000 - 99,999', 'USD 50,000 - 99,999'),
            ('USD 100,000 +', 'USD 100,000 +')
        )
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'offering')
        ordering = ['created_at']

    @cached_property
    @annotated
    def full_name(self):
        return str(self.user.profile.last_kyc.details)


class InvestmentApplication(models.Model):
    objects = InvestmentApplicationManager()
    STATUS_CHOICES = (
        (InvestmentApplicationStatus.DRAFT, _('Draft')),
        (InvestmentApplicationStatus.PENDING, _('Pending')),
        (InvestmentApplicationStatus.HOLD, _('Hold')),
        (InvestmentApplicationStatus.COMPLETED, _('Completed')),
        (InvestmentApplicationStatus.CANCELED, _('Canceled')),
        (InvestmentApplicationStatus.EXPIRED, _('Expired')),
        (InvestmentApplicationStatus.ERROR, _('Error')),
    )
    AGREEMENT_STATUS_CHOICES = (
        (InvestmentApplicationAgreementStatus.INITIAL, _('Initial')),
        (InvestmentApplicationAgreementStatus.PREPARING, _('Preparing')),
        (InvestmentApplicationAgreementStatus.PREPARED, _('Prepared')),
        (InvestmentApplicationAgreementStatus.VALIDATING, _('Validating')),
        (InvestmentApplicationAgreementStatus.SUCCESS, _('Success')),
        (InvestmentApplicationAgreementStatus.ERROR, _('Error')),
    )
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT, related_name='applications')
    offering = models.ForeignKey(Offering, on_delete=models.PROTECT, related_name='applications')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    deposit = models.ForeignKey(
        to='django_banking.Operation',
        on_delete=models.PROTECT,
        null=True,
        related_name='deposited_application',
    )
    deposit_reference_code = models.CharField(max_length=100, default=generate_deposit_reference_code)
    amount = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2,
        verbose_name=_('amount')
    )
    bank_account = models.ForeignKey(
        to='wire_transfer.ColdBankAccount',
        on_delete=models.PROTECT,
        blank=True, null=True
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES,
        default=InvestmentApplicationStatus.PENDING
    )

    is_agreed_risks = models.BooleanField(default=False)

    subscription_agreement_status = models.CharField(
        max_length=16, choices=AGREEMENT_STATUS_CHOICES,
        default=InvestmentApplicationAgreementStatus.INITIAL
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @cached_property
    def asset(self):
        return self.account.asset

    @cached_property
    def ownership(self):
        # return rounded(self.amount / self.offering.valuation, 6)
        return 0

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Investment {self.offering} - {self.user}'

    @cached_property
    def is_deposit_allowed(self):
        """
        New deposit allowed only if it not exist yet or previous is failed.
        """
        if self.status == InvestmentApplicationStatus.HOLD:
            return False
        if not bool(self.deposit_id):
            return True
        return not(
            self.deposit.is_processed or self.deposit.is_processing
        )

    def update_status(self, commit=True):
        # TODO completed status after share distribution
        self.status = {
            OperationStatus.NEW: InvestmentApplicationStatus.PENDING,
            OperationStatus.ACTION_REQUIRED: InvestmentApplicationStatus.PENDING,
            OperationStatus.HOLD: InvestmentApplicationStatus.HOLD,
            OperationStatus.COMMITTED: InvestmentApplicationStatus.HOLD,
            OperationStatus.CANCELLED: InvestmentApplicationStatus.PENDING,
            OperationStatus.DELETED: InvestmentApplicationStatus.PENDING,
            OperationStatus.ERROR: InvestmentApplicationStatus.PENDING
        }[self.deposit.status]
        if commit:
            self.save(update_fields=('deposit', 'status', 'amount'))

    @transaction.atomic
    def create_deposit(self, asset, amount, references, method, hold=False, commit=True):
        recipient_account = ColdBankAccount.objects.for_customer(self.user).account
        source_account = UserAccount.objects.for_customer(self.user, asset)
        self.deposit = Operation.objects.create_deposit(
            payment_method_account=recipient_account,
            user_account=source_account,
            amount=amount,
            references=references,
            method=method,
            hold=hold
        )
        self.update_status(commit=False)
        if commit:
            self.save(update_fields=['deposit', 'status'])
        return self.deposit

    @transaction.atomic
    def add_card_deposit(self, checkout_token=None, commit=True,
                         references=None):
        asset = Asset.objects.main_fiat_for_customer(self.user)
        references = references or {}
        references['reference_code'] = self.deposit_reference_code
        if checkout_token:
            references['checkout_token'] = checkout_token
        self.create_deposit(
            asset=asset,
            amount=self.amount,
            references=references,
            method=OperationMethod.CARD,
            hold=False,
            commit=commit
        )
        card_charge_request(
            deposit_id=self.deposit.pk,
            user_id=self.user.pk,
            checkout_token=checkout_token,
            amount=self.amount,
            reference_code=self.deposit_reference_code
        )
        return self.deposit

    @transaction.atomic
    def add_wire_transfer_deposit(self, swift_code, bank_name, holder_name, iban_number, amount=None, commit=True):
        """Creates payment for application
        This is temporary method which will help with further development of investment process

        For now, each application can have only one deposit which amount equals application's amount of funds.
        While user won't be able to withdraw funds, we can commit deposit operation, set HOLD status to application
        and don't create exchange operation.
        """
        asset = Asset.objects.main_fiat_for_customer(self.user)
        amount = amount or self.amount
        try:
            user_bank_account = UserBankAccount.objects.get(
                swift_code=swift_code,
                iban_number=iban_number,
                user=self.user,
            )
        except ObjectDoesNotExist:
            user_bank_account = UserBankAccount.objects.create(
                swift_code=swift_code,
                bank_name=bank_name,
                holder_name=holder_name,
                iban_number=iban_number,
                user=self.user,
                account=Account.objects.create(
                    asset=asset, type=AccountType.TYPE_NORMAL, strict=False
                ),
            )
        self.create_deposit(
            asset=asset,
            amount=amount,
            references={
                'reference_code': self.deposit_reference_code,
                'user_bank_account_uuid': str(user_bank_account.uuid),
            },
            method=OperationMethod.WIRE_TRANSFER,
            hold=True,
            commit=commit
        )
        return self.deposit

    @property
    def is_agreed_subscription(self):
        return self.subscription_agreement_status == InvestmentApplicationAgreementStatus.SUCCESS

    @transaction.atomic()
    def prepare_subscription_agreement(
        self,
        template,
        envelope_id,
        redirect_url,
    ):
        self.subscription_agreement_status = InvestmentApplicationAgreementStatus.PREPARED
        self.save(update_fields=('subscription_agreement_status',))
        SubscriptionAgreement.objects.create(
            template=template,
            application=self,
            envelope_id=envelope_id,
            envelope_status=SubscriptionAgreementEnvelopeStatus.SENT,
            redirect_url=redirect_url,
        )

    def start_validating_subscription_agreement(self):
        self.subscription_agreement_status = InvestmentApplicationAgreementStatus.VALIDATING
        self.save(update_fields=('subscription_agreement_status',))

    @transaction.atomic()
    def finish_subscription_agreement(
        self,
        envelope_status,
    ):
        self.agreement.envelope_status = envelope_status
        self.agreement.save(update_fields=('envelope_status',))
        update_fields = ['subscription_agreement_status']
        if self.agreement.envelope_status == SubscriptionAgreementEnvelopeStatus.COMPLETED:
            self.subscription_agreement_status = InvestmentApplicationAgreementStatus.SUCCESS
            self.status = InvestmentApplicationStatus.PENDING
            update_fields.append('status')
        else:
            self.subscription_agreement_status = InvestmentApplicationAgreementStatus.ERROR
        self.save(update_fields=update_fields)


class PersonalAgreement(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    offering = models.ForeignKey(Offering, on_delete=models.PROTECT)
    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)
    file = models.FileField(storage=personal_agreements_file_storage)
    is_agreed = models.BooleanField(default=False)

    class Meta:
        unique_together = ['offering', 'user']


class SubscriptionAgreementTemplate(models.Model):
    context_vars_getters: Dict[str, Callable[[InvestmentApplication], str]] = {
        'amount': lambda ia: ia.amount,
        'name': lambda ia: str(ia.user.profile.last_kyc.details),
        'address': lambda ia: ia.user.profile.last_kyc.details.address,
        'country': lambda ia: ia.user.profile.last_kyc.details.get_country_display(),
        'passport_number': lambda ia: ia.user.profile.last_kyc.details.passport_number,
    }

    name = models.CharField(max_length=320)
    offering = models.ForeignKey(to=Offering, null=True, on_delete=models.SET_NULL)
    template_id = models.UUIDField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['offering'], name='unique_active_for_offering', condition=Q(is_active=True))
        ]

    def __str__(self):
        return f'Template `{self.name}` - {self.offering}'

    def get_context(self, application: InvestmentApplication) -> Dict[str, str]:
        return {
            field: getter(application) for field, getter in self.context_vars_getters.items()
        }


class SubscriptionAgreement(models.Model):
    ENVELOPE_STATUS_CHOICES = (
        (SubscriptionAgreementEnvelopeStatus.COMPLETED, _('Completed')),
        (SubscriptionAgreementEnvelopeStatus.CREATED, _('Created')),
        (SubscriptionAgreementEnvelopeStatus.DECLINED, _('Declined')),
        (SubscriptionAgreementEnvelopeStatus.DELIVERED, _('Delivered')),
        (SubscriptionAgreementEnvelopeStatus.SENT, _('Sent')),
        (SubscriptionAgreementEnvelopeStatus.SIGNED, _('Signed')),
        (SubscriptionAgreementEnvelopeStatus.VOIDED, _('Voided')),
    )

    application = models.OneToOneField(to=InvestmentApplication, on_delete=models.CASCADE, related_name='agreement')
    template = models.ForeignKey(to=SubscriptionAgreementTemplate, on_delete=models.PROTECT, related_name='agreements')

    envelope_id = models.UUIDField()
    envelope_status = models.CharField(max_length=20, choices=ENVELOPE_STATUS_CHOICES)

    redirect_url = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
