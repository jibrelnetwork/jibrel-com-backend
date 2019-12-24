from django.dispatch import Signal

wire_transfer_deposit_approved = Signal(providing_args=[
    "instance",
])
wire_transfer_deposit_rejected = Signal(providing_args=[
    "instance",
])
wire_transfer_deposit_requested = Signal(providing_args=[
    "instance", "user_ip_address"
])
wire_transfer_withdrawal_approved = Signal(providing_args=[
    "instance",
])
wire_transfer_withdrawal_rejected = Signal(providing_args=[
    "instance",
])
wire_transfer_withdrawal_requested = Signal(providing_args=[
    "instance", "user_ip_address"
])
