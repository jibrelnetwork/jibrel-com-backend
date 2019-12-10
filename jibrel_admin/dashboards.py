from admin_tools.dashboard import Dashboard, modules


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


class CoinMenaIndexDashboard(Dashboard):

    def init_with_context(self, context):
        request = context['request']
        # append an app list module for "Applications"
        self.children.append(CustomModelList(
            'Customers',
            models=('jibrel.authentication.models.User',)
        ))
        self.children.append(CustomModelList(
            'Bank accounts',
            models=(
                'jibrel.payments.models.*WireTransferOperation*',
            )
        ))
        self.children.append(CustomModelList(
            'Card payments',
            models=(
                'jibrel.payments.models.*CardOperation*',
            )
        ))
        self.children.append(CustomModelList(
            'Crypto payments',
            models=(
                'jibrel.payments.models.*Crypto*',
            )
        ))
        self.children.append(CustomModelList(
            'Compliance',
            models=(
                'jibrel.kyc.models.IndividualKYCSubmission',
                'jibrel.kyc.models.OrganisationalKYCSubmission',
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
                    'jibrel.assets.models.AssetPair',
                    'jibrel.payments.models.DepositBankAccount',
                    'jibrel.payments.models.Fee',
                )
            ))
            # append an app list module for "Administration"
            self.children.append(CustomModelList(
                'Administration',
                models=('django.contrib.*', 'constance.*'),
            ))

        # append a recent actions module
        self.children.append(modules.RecentActions('Recent Actions', 5))
