from django.contrib import admin

from django_banking.contrib.wire_transfer.models import (
    WithdrawalWireTransferOperation
)

admin.site.unregister(WithdrawalWireTransferOperation)
