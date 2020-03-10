class CheckoutStatus:
    PENDING = 'pending'
    AUTHORIZED = 'authorized'
    VERIFIED = 'card verified'
    VOIDED = 'voided'
    PARTIALLY_CAPTURED = 'partially captured'
    CAPTURED = 'captured'
    PARTIALLY_REFUNDED = 'partially refunded'
    REFUNDED = 'refunded'
    DECLINED = 'declined'
    CANCELLED = 'cancelled'
    PAID = 'paid'


class WebhookType:
    CARD_VERIFIED = "card_verified"
    CARD_VERIFICATION_DECLINED = "card_verification_declined"
    DISPUTE_CANCELED = "dispute_canceled"
    DISPUTE_EVIDENCE_REQUIRED = "dispute_evidence_required"
    DISPUTE_EXPIRED = "dispute_expired"
    DISPUTE_LOST = "dispute_lost"
    DISPUTE_RESOLVED = "dispute_resolved"
    DISPUTE_WON = "dispute_won"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_DECLINED = "payment_declined"
    PAYMENT_EXPIRED = "payment_expired"
    PAYMENT_CANCELED = "payment_canceled"
    PAYMENT_VOIDED = "payment_voided"
    PAYMENT_VOID_DECLINED = "payment_void_declined"
    PAYMENT_CAPTURED = "payment_captured"
    PAYMENT_CAPTURE_DECLINED = "payment_capture_declined"
    PAYMENT_CAPTURE_PENDING = "payment_capture_pending"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_REFUND_DECLINED = "payment_refund_declined"
    PAYMENT_REFUND_PENDING = "payment_refund_pending"
    PAYMENT_CHARGEBACK = "payment_chargeback"
    PAYMENT_RETRIEVAL = "payment_retrieval"
    SOURCE_UPDATED = "source.updated"
    PAYMENT_PAID = "payment_paid"
