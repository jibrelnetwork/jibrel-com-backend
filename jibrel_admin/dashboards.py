from admin_tools.dashboard import (
    Dashboard,
    modules
)


class CustomModelList(modules.ModelList):
    """
    Added support of view permissions
    """

    template = 'admin_tools/dashboard/modules/model_list.html'

    def init_with_context(self, context):
        if self._initialized:
            return
        items = self._visible_models(context['request'])
        if not items:
            return
        for model, perms in items:
            model_dict = {}
            model_dict['title'] = model._meta.verbose_name_plural
            if perms.get('change') or perms.get('view'):
                model_dict['view_only'] = not perms.get('change')
                model_dict['change_url'] = self._get_admin_change_url(model, context)
            if perms['add']:
                model_dict['add_url'] = self._get_admin_add_url(model, context)
            self.children.append(model_dict)

        self._initialized = True


class IndexDashboard(Dashboard):
    def init_with_context(self, context):
        request = context['request']
        # append an app list module for "Applications"
        self.children.append(CustomModelList(
            'Customers',
            models=('jibrel.authentication.models.User',)
        ))

        self.children.append(CustomModelList(
            'Compliance',
            models=(
                'jibrel.kyc.models.IndividualKYCSubmission',
                'jibrel.kyc.models.OrganisationalKYCSubmission',
            )
        ))
        self.children.append(CustomModelList(
            'Campaigns',
            models=(
                'jibrel.campaigns.*',
                'jibrel.investment.*',
            ),
            exclude=(
                'jibrel.investment.models.SubscriptionAgreementTemplate',
            )
        ))

        if request.user.is_active and request.user.is_superuser:
            self.children.append(CustomModelList(
                'Exchanges',
                models=(
                    'jibrel.exchanges.models.ExchangeOperation',
                )
            ))
            self.children.append(CustomModelList(
                'Settings',
                models=(
                    'jibrel.investment.models.SubscriptionAgreementTemplate',
                )
            ))
            # append an app list module for "Administration"
            self.children.append(CustomModelList(
                'Administration',
                models=(
                    'jibrel.authentication.models.OneTimeToken',
                    'django.contrib.*',
                    # 'constance.*',
                    'jibrel.notifications.models.*'
                ),
            ))
            self.children.append(CustomModelList(
                'Payment settings',
                models=(
                    'django_banking.models.*',
                    'django_banking.contrib.wire_transfer.models.ColdBankAccount',
                ),
            ))
            self.children.append(CustomModelList(
                'Wire Transfer',
                models=(
                    'django_banking.contrib.wire_transfer.models.DepositWireTransferOperation',
                    'django_banking.contrib.wire_transfer.models.WithdrawalWireTransferOperation',
                    'django_banking.contrib.wire_transfer.models.RefundWireTransferOperation',
                ),
            ))
            self.children.append(CustomModelList(
                'Card',
                models=(
                    'django_banking.contrib.card.models.DepositCardOperation',
                    'django_banking.contrib.card.models.WithdrawalCardOperation',
                    'django_banking.contrib.card.models.RefundCardOperation',
                ),
            ))

            self.children.append(CustomModelList(
                'Wallets Backups',
                models=(
                    'jibrel.wallets.models.*',
                ),
            ))

        # append a recent actions module
        self.children.append(modules.RecentActions('Recent Actions', 5))
