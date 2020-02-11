FROM python:3.7-alpine

ARG ENVIRONMENT="production"
ARG EMAIL_TEMPLATES_DIR="jibrel-com-emails/dist"
ARG STATIC_ROOT="/static"

ENV ENVIRONMENT=$ENVIRONMENT \
    EMAIL_TEMPLATES_DIR=$EMAIL_TEMPLATES_DIR \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=0.12.17 \
    ENVIRONMENT=${ENVIRONMENT} \
    PORT=8000 \
    DJANGO_SECRET_KEY="" \
    DJANGO_ALLOWED_HOSTS="localhost" \
    MAIN_DB_NAME="" \
    MAIN_DB_USER="" \
    MAIN_DB_USER_PASSWORD="" \
    MAIN_DB_HOST="" \
    MAIN_DB_PORT=5432 \
    ADMIN_DB_NAME="" \
    ADMIN_DB_USER="" \
    ADMIN_DB_USER_PASSWORD="" \
    ADMIN_DB_HOST="" \
    ADMIN_DB_PORT=5432 \
    STATIC_ROOT=$STATIC_ROOT \
    TWILIO_API_URL="https://verify.twilio.com/v2" \
    TWILIO_ACCOUNT_SID="" \
    TWILIO_AUTH_TOKEN="" \
    TWILIO_VERIFICATION_SERVICE_SID="" \
    CELERY_BROKER_URL="" \
    CELERY_RESULT_BACKEND="" \
    MAILGUN_API_URL="https://api.mailgun.net/v3" \
    MAILGUN_API_KEY="" \
    MAILGUN_SENDER_DOMAIN="" \
    MAILGUN_FROM_EMAIL="" \
    SEND_VERIFICATION_TIME_LIMIT="60" \
    FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT="3600" \
    FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT="2" \
    VERIFICATION_SESSION_LIFETIME="600" \
    KYC_DATA_LOCATION="kyc" \
    PERSONAL_AGREEMENTS_DATA_LOCATION="persoanl_agreements" \
    AWS_ACCESS_KEY_ID="" \
    AWS_SECRET_ACCESS_KEY="" \
    AWS_S3_REGION_NAME="" \
    AWS_STORAGE_BUCKET_NAME="" \
    VERIFY_EMAIL_TOKEN_LIFETIME="86400" \
    VERIFY_EMAIL_SEND_TOKEN_ATTEMPT_COUNT="5" \
    VERIFY_EMAIL_SEND_TOKEN_TIME_LIMIT="3600" \
    VERIFY_EMAIL_SEND_TOKEN_TIMEOUT="180" \
    FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME="7200" \
    FORGOT_PASSWORD_SEND_TOKEN_ATTEMPT_COUNT="5" \
    FORGOT_PASSWORD_SEND_TOKEN_TIME_LIMIT="3600" \
    FORGOT_PASSWORD_SEND_TOKEN_TIMEOUT="180" \
    SENTRY_DSN="" \
    DOMAIN_NAME="localhost" \
    SUBDOMAINS="" \
    LOG_LEVEL="INFO" \
    UPLOAD_KYC_DOCUMENT_COUNT="20" \
    UPLOAD_KYC_DOCUMENT_TIME_LIMIT="3600" \
    ONFIDO_API_KEY="" \
    PRIVATE_KRAKEN_API_KEY="" \
    PRIVATE_KRAKEN_SIGN_KEY="" \
    KYC_ADMIN_NOTIFICATION_RECIPIENT="" \
    KYC_ADMIN_NOTIFICATION_PERIOD="1" \
    DOCU_SIGN_ACCOUNT_ID='' \
    DOCU_SIGN_RETURN_URL_TEMPLATE=''

RUN wget https://github.com/jibrelnetwork/dockerize/releases/latest/download/dockerize-linux-amd64-latest.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-latest.tar.gz \
    && rm dockerize-linux-amd64-latest.tar.gz

RUN addgroup -g 82 app \
 && adduser -S -u 82 -g app app \
 && mkdir -p /app ${STATIC_ROOT}\
 && chown -R app:app /app ${STATIC_ROOT}

RUN apk update \
    && apk add --no-cache build-base postgresql-dev zlib-dev jpeg-dev libffi-dev \
    && pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY --chown=app:app poetry.lock pyproject.toml /app/
RUN poetry config settings.virtualenvs.create false \
    && poetry install $(test "$ENVIRONMENT" == production && echo "--no-dev") --no-interaction --no-ansi

COPY --chown=app:app . /app
#COPY ./jibrel-emails/dist $EMAIL_TEMPLATES_DIR

USER app

ENTRYPOINT ["/app/run.sh"]
