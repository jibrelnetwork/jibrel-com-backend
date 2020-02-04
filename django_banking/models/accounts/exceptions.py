class AccountingException(Exception):
    pass


class AccountException(AccountingException):
    def __init__(self, account, reason=None):
        self.account = account
        if reason:
            self.reason = reason


class AccountBalanceException(AccountException):
    reason = "Account balance doesn't met its type rules."
