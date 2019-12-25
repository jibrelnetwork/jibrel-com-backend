#!/bin/sh -e


dockerize -timeout 1m -wait tcp://${MAIN_DB_HOST:-main_db}:${MAIN_DB_PORT:-5432}
dockerize -timeout 1m -wait tcp://`python -c 'import os; p = os.getenv("CELERY_BROKER_URL", "").split("//", 1)[-1].split("@")[1]; print(p)'`


if [[ "$1" = "api" ]]; then
    echo "Starting jibrel.com backend service in '${ENVIRONMENT}' environment on node `hostname`"
#    python manage.py check
#    python manage.py migrate --noinput
    if [ "${ENVIRONMENT}" = "production" ]; then
        gunicorn jibrel.wsgi \
          -w 4 \
          -b 0.0.0.0:${PORT} \
          --log-file=- \
          --log-level ${LOG_LEVEL}
    else
        python /app/manage.py runserver 0.0.0.0:${PORT}
    fi
elif [[ "$1" = "admin" ]]; then
    echo "Starting jibrel.com admin service in '${ENVIRONMENT}' environment on node `hostname`"
    python manage.py check --settings jibrel_admin.settings
    python manage.py migrate --noinput --settings jibrel_admin.settings
    {
      echo "import os;"
      echo "from django.contrib.auth import get_user_model;"
      echo "User = get_user_model();"
      echo "pwd = os.getenv('ADMIN_PASSWORD', 'admin');"
      echo "admin = User.objects.filter(username='admin').first();"
      echo "if admin is None: User.objects.create_superuser('admin', 'admin@example.com', pwd) and print('Admin user created')"
      echo "if admin is not None: admin.set_password(pwd); admin.save() and print('Admin password was reset')"
    } | python manage.py shell --settings jibrel_admin.settings
    if [ "${ENVIRONMENT}" = "production" ]; then
        python manage.py collectstatic --noinput --settings jibrel_admin.settings
        gunicorn jibrel_admin.wsgi \
          -w 4 \
          -b 0.0.0.0:${PORT} \
          --log-file=- \
          --log-level ${LOG_LEVEL}
    else
        python /app/manage.py runserver 0.0.0.0:${PORT} --settings jibrel_admin.settings
    fi
elif [[ "$1" = "celeryworker" ]]; then
    echo "Starting jibrel.com worker"
    celery -A jibrel worker -l ${LOG_LEVEL} ${@:13}
elif [[ "$1" = "celerybeat" ]]; then
    echo "Starting jibrel.com celery beat"
    celery -A jibrel beat -l ${LOG_LEVEL}
else
    exec "$@"
fi
