from django.utils.functional import cached_property

from ...models import Operation
from .managers import (
    DepositCardOperationManager,
    RefundCardOperationManager,
    WithdrawalCardOperationManager
)


class DepositCardOperation(Operation):
    objects = DepositCardOperationManager()

    def action_required(self):
        # TODO dynamically switch backend
        print(self)
        # print(self.charge_checkout.redirect_link)
        print(123)
        return self.charge_checkout.latest('created_at').redirect_link

    class Meta:
        proxy = True


class WithdrawalCardOperation(Operation):
    objects = WithdrawalCardOperationManager()

    class Meta:
        proxy = True


class RefundCardOperation(Operation):
    objects = RefundCardOperationManager()

    class Meta:
        proxy = True

    @cached_property
    def deposit(self):
        return DepositCardOperation.objects.get(
            pk=self.references['deposit']
        )
