from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from django_banking import logger
from tap_payments import get_tap_client


class IsCardOwner(BasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj: str):
        customer_id = request.user.profile.tap_customer_id
        with get_tap_client() as client:
            # TODO: add cache
            user_cards = client.get_card_list(customer_id)

        for card in user_cards:
            if card.id == obj:
                return True

        logger.error("User %s requested deposit from card %s that isn't in "
                     "his card list", request.user, obj)
        raise ValidationError('card_id', 'Invalid card id')
