from django_banking.models.accounts.exceptions import AccountingException


class OperationException(AccountingException):
    def __init__(self, operation, reason=None):
        self.operation = operation
        if reason:
            self.reason = reason


class OperationBalanceException(OperationException):
    def __init__(self, operation, asset):
        self.operation = operation
        self.asset = asset
        super().__init__(
            operation,
            reason="Transactions balance not qual to 0 for asset %s" % asset
        )


class TransactionException(AccountingException):
    def __init__(self, transaction, reason=None):
        self.transaction = transaction
        if reason:
            self.reason = reason


class AccountStrictnessException(TransactionException):
    reason = "Credit operations not allowed for strict accounts."


class OperationAccountException(OperationException):
    def __init__(self, operation, account, reason):
        pass


class OperationTransactionException(OperationException):
    def __init__(self, operation, account, transaction):
        pass
