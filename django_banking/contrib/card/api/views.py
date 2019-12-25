
class CardListAPIView(APIView):

    """List saved plastic cards saved by authenticated user.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsKYCVerifiedUser)

    def get(self, request):
        customer_id = get_or_create_tap_customer_id(request.user)

        # TODO: cache
        with get_tap_client() as tap_client:
            try:
                cards = tap_client.get_card_list(customer_id)
            except InvalidCustomer:
                logger.error("Invalid customer id saved in db for user %s",
                             request.user)
                raise InvalidException('card_id', 'Invalid customer')
            except TapClientException:
                logger.exception("Unpredicted TAP error")
                # TODO: specific exception/code?
                raise InvalidException('card_id', 'Payment gateway error')

        return Response({
            "data": {
                "customerId": customer_id,
                "cards": CardSerializer(cards, many=True).data
            }
        })


class CardDepositAPIView(APIView):

    """Start TAP deposit routine.

    Create charge on tap side, and return redirect url for user (in case of
    3d secure) or transaction id if already charged.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsKYCVerifiedUser, IsCardOwner)

    def post(self, request, card_id):
        self.check_object_permissions(request, card_id)

        amount = sanitize_amount(request.data['amount'])
        asset = Asset.objects.main_fiat_for_customer(request.user)
        customer_id = request.user.profile.tap_customer_id

        operation = create_charge_operation(request.user, asset, card_id,
                                            amount, hold=False)

        redirect_url = settings.APP_OPERATION_LINK.format(operation_id=operation.uuid)

        with get_tap_client() as tap_client:
            try:
                card = tap_client.get_card(customer_id, card_id)
                charge = tap_client.create_charge(
                    customer_id=customer_id,
                    amount=amount,
                    currency=asset,
                    redirect_url=redirect_url,
                    card_id=card_id
                )
            except InvalidCustomer:
                logger.error("Invalid customer id saved in db for user %s",
                             request.user)
                raise InvalidException('card_id', 'Invalid customer')
            except InvalidCardId:
                logger.error("Invalid card id %s for customer %s (user %s)",
                             card_id, customer_id, request.user)
                # TODO: specific exception/code?
                raise InvalidException('card_id', 'Invalid card id')
            except TapClientException:
                logger.exception("Unpredicted TAP error")
                # TODO: specific exception/code?
                raise InvalidException('card_id', 'Payment gateway error')

        operation = process_tap_charge(request.user, charge, card)

        if charge.status == ChargeStatus.INITIATED and charge.transaction.url:
            return Response({
                'data': {
                    'redirect_url': charge.transaction.url
                }
            })
        elif charge.status == ChargeStatus.CAPTURED:
            return Response({
                'data': {
                    'operationId': operation.uuid
                }
            })
        else:
            raise ValidationError("amount", "Card payment exception")


class CardChargeAPIView(APIView):

    """Get operation id for tap charge id.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsKYCVerifiedUser, IsCardOwner)

    def post(self, request, card_id):
        self.check_object_permissions(request, card_id)

        charge_id = request.data.get('charge_id')
        if not charge_id:
            raise InvalidException('charge_id', 'Required field', 'required')

        with get_tap_client() as tap_client:
            try:
                charge = tap_client.get_charge(charge_id)
            except InvalidChargeId:
                raise InvalidException('charge_id', 'Invalid charge id',
                                       'invalid')

            # TODO: handle errors
            try:
                card = tap_client.get_card(
                    request.user.profile.tap_customer_id,
                    card_id
                )
            except InvalidCustomer:
                logger.error("Invalid customer id saved in db for user %s",
                             request.user)
                raise InvalidException('charge_id', 'Invalid customer')
            except InvalidCardId:
                logger.error("Invalid card id %s for customer %s (user %s)",
                             card_id, charge.customer, request.user)
                # TODO: specific exception/code?
                raise InvalidException('charge_id', 'Invalid card id')
            except TapClientException:
                logger.exception("Unpredicted TAP error")
                # TODO: specific exception/code?
                raise InvalidException('charge_id', 'Payment gateway error')

        operation = process_tap_charge(request.user, charge, card)

        return Response({
            'data': {
                'operationId': str(operation.uuid)
            }
        })
