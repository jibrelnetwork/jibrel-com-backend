from django.conf import settings
from pylama.pytest import PylamaItem


def pytest_collection_modifyitems(session, config, items):
    """Filter test items.

    If both `--pylama` and `--pylama-only` passed, only pylama test items will
    be selected for execution.
    """
    if config.getoption('--pylama') and config.getoption('--pylama-only'):
        items[:] = [item for item in items if isinstance(item, PylamaItem)]


def pytest_addoption(parser):
    """Extend CLI params.

    Add --pylama-only option.
    """
    parser.addoption('--pylama-only', default=False, action='store_true')


pytest_plugins = (
    'tests.fixtures',
    # 'tests.test_exchanges.fixtures',
    # 'tests.test_payments.fixtures',
)


def pytest_configure(config):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': ()
    }

    if not config.getoption('--pylama-only'):
        from constance import config
        config.TRADING_IS_ACTIVE = True
