# jibrelcom-backend

Jibrel.com backend service.

# Getting started

Clone repo with submodules:

```bash
git clone git@github.com:jibrelnetwork/jibrel-com-backend.git
cd jibrel-com-backend
git submodule init
git submodule update
```

Run using docker-compose:

```bash
docker-compose up -d db
docker-compose up -d broker
docker-compose up -d api
docker-compose up -d worker
```

# Configuration

## Database 

Jibrel.com backend service requires PostgreSQL database which can be configured with environment variables:

- MAIN_DB_HOST (localhost etc.)
- MAIN_DB_NAME (jibrel_db etc.)
- MAIN_DB_USER (postgres etc.)
- MAIN_DB_USER_PASSWORD
- MAIN_DB_PORT (default 5432)

# Admin

Jibrel.com admin service requires PostgreSQL database  which can be configured with environment variables:

- ADMIN_DB_HOST (localhost etc.)
- ADMIN_DB_NAME (jibrel_admin_db etc.)
- ADMIN_DB_USER (postgres etc.)
- ADMIN_DB_USER_PASSWORD
- ADMIN_DB_PORT (default 5432)

To create admin user, provide `ADMIN_PASSWORD` env variable to jibrel-admin container. 
Admin user `admin` will be created if didn't exist yet.

## Redis

We use Redis as fast Key-Value storage, environment variables below should be passed to container:
- REDIS_HOST
- REDIS_PORT
- REDIS_DB
- REDIS_PASSWORD

## Sentry

- SENTRY_DSN (empty by default)

## Message broker
We use RabbitMQ as message broker for background tasks, for this purpose you should provide ampq URL as environment variable named **CELERY_BROKER_URL** 

## Django
Web application starts at port 8000 by default, to override this behavior use *PORT* environment variable.
Django additionally requires secret key (env *DJANGO_SECRET_KEY*) for framework's cryptographic internals.   

For properly working Django application needs to know host where it was started, fill the *DJANGO_ALLOWED_HOSTS* env 
with addresses split by space ("localhost jibrel.com" etc.) 

## File storing
We use AWS S3 for storing files uploaded by users. You must specify environment variables:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_STORAGE_BUCKET_NAME
- AWS_S3_REGION_NAME 

For files uploaded while KYC verification process you can provide specific location in bucket:
 - KYC_DATA_LOCATION (default: kyc)
 
 You can use **AWS_S3_LOCATION_PREFIX** (default: empty string) to split one bucket between different environments (
 testing, development, etc.). Example: if AWS_S3_LOCATION_PREFIX=testing then your KYC files would be uploaded to
 testing/kyc location.

## Phone Verification
To verify phone number of our customers we use Twilio API, workflow described 
[here](https://www.twilio.com/docs/verify/api-beta#phone-verification-workflow).
We have to create Twilio Verify Service with **CODE LENGTH** parameter equals **6**.
After registration and service creation provide environment variables:

- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_VERIFICATION_SERVICE_SID
- TWILIO_REQUEST_TIMEOUT — used as request timeout for twilio requests in seconds (5 by default)

## DOMAIN_NAME and SUBDOMAINS
You have to provide these environment variables to get access to backend service. Example:
```
DOMAIN_NAME=jibrel.com
SUBDOMAINS=app1,app2
```
In this case, CSRF and Session cookie will be set to domain `.jibrel.com`, CORS protected endpoints will response
 the right `Access-Control-Allow-Origin` header for `jibrel.com`, `app1.jibrel.com` or `app2.jibrel.com` origins.

# Developer tips

## Using Postman

You can import `v1.swagger.yml` into Postman to get collection. After that, you may edit collection to configure Authentication & Authorization.
On **Edit Collection** window in **Authentication** tab:
- **TYPE**=**API Key**
- **Key**=**X-CSRFToken**
- **Value**=**{{csrftoken}}**
- **Add to**=**Header**

Then, on tab **Tests** ad code below:
```javascript
var xsrfCookie = postman.getResponseCookie("csrftoken");
postman.setEnvironmentVariable('csrftoken', xsrfCookie.value);
```
