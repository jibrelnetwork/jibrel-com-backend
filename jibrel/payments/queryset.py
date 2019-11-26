from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Case, Exists, F, OuterRef, Q, Subquery, Sum, When
from django.db.models.functions import Abs, Coalesce

from jibrel.authentication.models import User
from jibrel.accounting.models import Asset, Operation, Transaction


class OperationQuerySet(models.QuerySet):
    def deposit_crypto(self):
        return self.filter(
            transactions__account__asset__type=Asset.CRYPTO,
            type=Operation.DEPOSIT
        ).distinct()

    def deposit_wire_transfer(self):
        return self.filter(
            tapcharge__isnull=True,
            transactions__account__asset__type=Asset.FIAT,
            type=Operation.DEPOSIT
        ).distinct()

    def deposit_card(self):
        return self.filter(
            tapcharge__isnull=False,
            transactions__account__asset__type=Asset.FIAT,
            type=Operation.DEPOSIT,
        ).distinct()

    def withdrawal_wire_transfer(self):
        return self.filter(
            tapcharge__isnull=True,
            transactions__account__asset__type=Asset.FIAT,
            type=Operation.WITHDRAWAL,
        ).distinct()

    def withdrawal_crypto(self):
        return self.filter(
            transactions__account__asset__type=Asset.CRYPTO,
            type=Operation.WITHDRAWAL,
        ).distinct()

    def withdrawal_card(self):
        return self.filter(
            tapcharge__isnull=False,
            transactions__account__asset__type=Asset.FIAT,
            type=Operation.WITHDRAWAL,
        ).distinct()

    def with_asset(self):
        """Annotates asset symbol and asset id for Deposit/Withdrawal operations"""

        return self.annotate(
            asset=Subquery(
                Transaction.objects
                    .filter(operation=OuterRef('pk'))
                    .values('account__asset__symbol')[:1]
            ),
            asset_id=Subquery(
                Transaction.objects
                    .filter(operation=OuterRef('pk'))
                    .values('account__asset_id')[:1]
            )
        )

    def with_fee(self):
        """Annotates fee for Deposit/Withdrawal operations"""
        from .models import FeeUserAccount

        return self.annotate(
            fee=Case(
                When(
                    type__in=[Operation.DEPOSIT, Operation.WITHDRAWAL],
                    then=Coalesce(
                        Subquery(
                            Transaction.objects
                                .annotate(is_fee_tx=Exists(FeeUserAccount.objects.filter(account=OuterRef('account'))))
                                .filter(operation=OuterRef('pk'), is_fee_tx=True)
                                .values('operation')
                                .annotate(total=Abs(Sum('amount')))
                                .values('total')[:1],
                            output_field=models.DecimalField()
                        ),
                        0)
                ),
                output_field=models.DecimalField()
            )
        )

    def with_amount(self):
        """Annotates debit/credit amount (including fee) for Deposit/Withdrawal operations"""

        return self.annotate(
            amount=Case(
                When(
                    type=Operation.DEPOSIT,
                    then=Subquery(
                        Transaction.objects
                            .filter(operation=OuterRef('pk'))
                            .values('operation')
                            .annotate(total=Abs(Sum('amount', filter=Q(amount__gt=0))))
                            .values('total')[:1]
                    ),
                ),
                When(
                    type=Operation.WITHDRAWAL,
                    then=Subquery(
                        Transaction.objects
                            .filter(operation=OuterRef('pk'))
                            .values('operation')
                            .annotate(total=Abs(Sum('amount', filter=Q(amount__lt=0))))
                            .values('total')[:1]
                    ),
                ),
                output_field=models.DecimalField()
            )
        )

    def with_total_amount(self):
        """Annotates total pay in/out amount (excluding fee) for Deposit/Withdrawal operations"""

        return self.annotate(
            total_amount=Case(
                When(type=Operation.DEPOSIT, then=F('amount') + F('fee')),
                When(type=Operation.WITHDRAWAL, then=F('amount') - F('fee')),
                output_field=models.DecimalField()
            ),
        )


class PaymentOperationQuerySet(models.QuerySet):
    def with_amounts(self, user: User):
        from .models import (
            UserAccount,
            FeeUserAccount
        )
        user_accounts = UserAccount.objects.get_user_accounts(user)
        fee_accounts = FeeUserAccount.objects.get_user_accounts(user)

        user_transactions = Transaction.objects.filter(
            operation=OuterRef('pk'),
            account__in=user_accounts,
        ).order_by().values('operation')
        fee_transactions = Transaction.objects.filter(
            operation=OuterRef('pk'),
            account__in=fee_accounts,
        ).order_by().values('operation')

        default_user_amount = user_transactions.annotate(total=Sum('amount')).values('total')[:1]
        default_user_asset_symbol = user_transactions.values('account__asset__symbol')[:1]
        default_user_asset_id = user_transactions.values('account__asset_id')[:1]
        default_fee_amount = fee_transactions.annotate(total=Sum('amount')).values('total')[:1]
        default_fee_asset_symbol = fee_transactions.values('account__asset__symbol')[:1]
        default_fee_asset_id = fee_transactions.values('account__asset_id')[:1]
        default_if_none = Decimal(0).quantize(Decimal(10) ** -settings.ACCOUNTING_DECIMAL_PLACES)

        debit_buy_amount = user_transactions.annotate(
            total=Sum(
                'amount',
                filter=Q(amount__gt=0)  # we should query like for sell but
                # filter by amount fits onto business logic and produces less JOINs
            )
        ).values('total')[:1]
        debit_sell_amount = user_transactions.annotate(
            total=Sum(
                'amount',
                filter=Q(account__asset__type=Asset.FIAT)
            )
        ).values('total')[:1]

        debit_buy_asset = user_transactions.filter(account__asset__type=Asset.CRYPTO)
        debit_sell_asset = user_transactions.filter(account__asset__type=Asset.FIAT)

        credit_buy_amount = user_transactions.annotate(
            total=Sum(
                'amount',
                filter=Q(amount__lt=0)  # we should query like for sell but
                # filter by amount fits onto business logic and produces less JOINs
            )
        ).values('total')[:1]
        credit_sell_amount = user_transactions.annotate(
            total=Sum(
                'amount',
                filter=Q(account__asset__type=Asset.CRYPTO)
            )
        ).values('total')[:1]
        credit_buy_asset = user_transactions.filter(account__asset__type=Asset.FIAT)
        credit_sell_asset = user_transactions.filter(account__asset__type=Asset.CRYPTO)

        return self.annotate(
            debit_amount=Coalesce(
                Case(
                    When(type=Operation.BUY, then=Subquery(debit_buy_amount)),
                    When(type=Operation.SELL, then=Subquery(debit_sell_amount)),
                    default=Subquery(default_user_amount),
                    output_field=models.DecimalField()
                ),
                default_if_none
            ),
            debit_asset=Case(
                When(type=Operation.BUY, then=Subquery(debit_buy_asset.values('account__asset__symbol')[:1])),
                When(type=Operation.SELL, then=Subquery(debit_sell_asset.values('account__asset__symbol')[:1])),
                default=Subquery(default_user_asset_symbol),
            ),
            debit_asset_id=Case(
                When(type=Operation.BUY, then=Subquery(debit_buy_asset.values('account__asset_id')[:1])),
                When(type=Operation.SELL, then=Subquery(debit_sell_asset.values('account__asset_id')[:1])),
                default=Subquery(default_user_asset_id),
            ),
            credit_amount=Abs(Coalesce(
                Case(
                    When(type=Operation.BUY, then=Subquery(credit_buy_amount)),
                    When(type=Operation.SELL, then=Subquery(credit_sell_amount)),
                    default=Subquery(default_user_amount),
                    output_field=models.DecimalField()
                ),
                default_if_none
            )),
            credit_asset=Case(
                When(type=Operation.BUY, then=Subquery(credit_buy_asset.values('account__asset__symbol')[:1])),
                When(type=Operation.SELL, then=Subquery(credit_sell_asset.values('account__asset__symbol')[:1])),
                default=Subquery(default_user_asset_symbol),
            ),
            credit_asset_id=Case(
                When(type=Operation.BUY, then=Subquery(credit_buy_asset.values('account__asset_id')[:1])),
                When(type=Operation.SELL, then=Subquery(credit_sell_asset.values('account__asset_id')[:1])),
                default=Subquery(default_user_asset_id),
            ),
            fee_amount=Coalesce(Subquery(default_fee_amount), default_if_none, output_field=models.DecimalField()),
            fee_asset=Subquery(default_fee_asset_symbol),
            fee_asset_id=Subquery(default_fee_asset_id),
        )

    def for_user(self, user: User, only_allowed_assets=True):
        from .models import UserAccount
        user_accounts = UserAccount.objects.get_user_accounts(user, only_allowed_assets)
        return self.filter(transactions__account__in=user_accounts).distinct()
