# import logging
#
# from django.conf import settings
# from requests import HTTPError
#
# from django_banking.user import User
# from tap_payments import (
#     Charge,
#     ChargeStatus,
#     get_tap_client,
#     process_tap_charge
# )
#
# logger = logging.getLogger(__name__)
#
#
# @app.task(bind=True, retry_backoff=5, autoretry_for=(HTTPError,))
# def process_charge(self, charge):
#     charge = Charge.from_dict(charge)
#     # TODO: handle special sources `src_kw.knet` etc
#     try:
#         customer = User.objects.get(profile__tap_customer_id=charge.customer.id)
#     except User.DoesNotExist:
#         # TODO: replace with error for real account (only)
#         logger.debug("Skip charge %s because customer id %s didn't "
#                      "match any customer in our database",
#                      charge, charge.customer.id)
#         return
#
#     with get_tap_client() as client:
#         charge_token = client.get_token(charge.source.id)
#
#         card = client.get_card(charge.customer.id, charge_token.card.id)
#
#         try:
#             process_tap_charge(customer, charge, card)
#         except ValidationError:
#             logger.exception("Charge %s processing exception (skip)", charge)
#             return
#
#         if charge.status == ChargeStatus.INITIATED:
#             logger.info("Retry processing of INITIATED charge %s", charge)
#             raise self.retry()
#
#
# @app.task(expires=settings.TAP_CHARGE_PROCESSING_SCHEDULE)
# def fetch_charges():
#     """Fetch all charges from tap and process them.
#     """
#     max_depth = 4
#     starting_after = None
#
#     with get_tap_client() as client:
#         for i in range(max_depth):
#             charges = client.get_charge_list(starting_after=starting_after)
#
#             for charge in charges:
#                 process_charge.delay(charge.to_dict())
#                 starting_after = charge.id
#
#             if not charges.has_more:
#                 break
