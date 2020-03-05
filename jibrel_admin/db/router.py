from django.conf import settings

# app labels
MAIN_DB_APPS = {
    'authentication',
    'kyc',
    'accounting',
    'assets',
    'payments',
    'exchanges',
    'notifications',
    'campaigns',
    'django_banking',
    'django_celery_results',
    'wire_transfer',
    'checkout',
    'investment',
    'wallets',
}


class MainDBRouter:
    main_db_alias = settings.MAIN_DB_NAME

    def db_for_read(self, model, **hints):
        if model._meta.app_label in MAIN_DB_APPS:
            return self.main_db_alias
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in MAIN_DB_APPS:
            return self.main_db_alias
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label in self.main_db_alias and obj2._meta.app_label in self.main_db_alias:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the auth app only appears in the 'auth_db'
        database.
        """
        if app_label in MAIN_DB_APPS:
            return db == self.main_db_alias
        return None
