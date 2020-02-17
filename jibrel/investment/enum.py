class InvestmentApplicationStatus:
    DRAFT = 'draft'
    PENDING = 'pending'
    HOLD = 'hold'  # hold funds for the further processing
    COMPLETED = 'completed'
    CANCELED = 'canceled'  # canceled by user
    EXPIRED = 'expired'  # not enough funds
    ERROR = 'error'  # funds has arrived but it is not meets a minimum investing amount


class InvestmentApplicationPaymentStatus:
    PAID = 'paid'
    NOT_PAID = 'not_paid'
    REFUND = 'refund'


class InvestmentApplicationAgreementStatus:
    INITIAL = 'initial'
    PREPARING = 'preparing'
    PREPARED = 'prepared'
    VALIDATING = 'validating'
    SUCCESS = 'success'
    ERROR = 'error'


class SubscriptionAgreementEnvelopeStatus:
    #: The envelope has been completed and all tags have been signed.
    COMPLETED = 'completed'
    #: The envelope is created as a draft. It can be modified and sent later.
    CREATED = 'created'
    #: The envelope has been declined by the recipients.
    DECLINED = 'declined'
    #: The envelope has been delivered to the recipients.
    DELIVERED = 'delivered'
    #: The envelope is sent to the recipients.
    SENT = 'sent'
    #: The envelope has been signed by the recipients.
    SIGNED = 'signed'
    #: The envelope is no longer valid and recipients cannot access or sign the envelope
    VOIDED = 'voided'
