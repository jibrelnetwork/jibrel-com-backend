from enum import Enum


class FeeOperationType(Enum):
    WITHDRAWAL_CRYPTO = 'withdrawal_crypto'
    WITHDRAWAL_BANK_ACCOUNT = 'withdrawal_bank_account'
    DEPOSIT_CRYPTO = 'deposit_crypto'
    DEPOSIT_BANK_ACCOUNT = 'deposit_bank_account'
    DEPOSIT_CARD = 'deposit_card'


class FeeValueType(Enum):
    CONSTANT = 'constant'
    PERCENTAGE = 'percentage'
