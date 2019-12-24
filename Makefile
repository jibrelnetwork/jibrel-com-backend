#!make
envfile = idea.env
ifneq ("$(wildcard $(envfile))","")
include $(envfile)
export $(shell sed 's/=.*//' $(envfile))
endif
cmd_mypy = mypy jibrel
# -fass, --force-alphabetical-sort-within-sections
# -e, --balanced
# -m, --multi-line
# -q, --quiet
# -rc, --recursive
# -fgw, --force-grid-wrap
# -d, --stdout
cmd_pylama = py.test --pylama --pylama-only -qq
cmd_isort = isort -rc -m 3 -e -fgw -q
cmd_test = pytest
api_name = $(shell basename $(CURDIR))_api_1
override_config = docker-compose.override.yml
minimum_apps = broker main_db redis admin_db

ifneq ("$(wildcard $(override_config))","")
ifneq ($(shell grep 's3local' $(override_config)),"")
minimum_apps := $(minimum_apps) s3local
endif
endif

fallback_text = "venv is not activated, starting docker"
params_passed = false

# for catch input arguments
RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
$(eval $(RUN_ARGS):;@:)

env:
	env

start:
ifeq ($(RUN_ARGS), all)
	@docker-compose up -d
else
	docker-compose up -d ${minimum_apps}
endif

rebuild:
	@docker-compose up -d --build

stop:
	@docker-compose down

logs:
	docker-compose logs -f --tail 50 $(RUN_ARGS)

clean:
	@docker-compose down -v

compose: # all input should contains in quotes. For example: make compose "run -u root --entrypoint sh api"
	docker-compose $(RUN_ARGS)
	exit 0

celery:
ifneq ($(VIRTUAL_ENV), "")
    ifeq ($(strip $(RUN_ARGS)),"")
    override RUN_ARGS = default,onfido
    endif

	@pip install watchdog > /dev/null
	echo "$(RUN_ARGS)"
	@watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A jibrel worker -Q $(RUN_ARGS) --concurrency=1 --loglevel=INFO -B
else
	@echo $(fallback_text)
    ifeq ($(RUN_ARGS), )
	@docker-compose start worker
    else
	@docker-compose start worker-$(RUN_ARGS)
    endif
endif

check:
ifneq ($(VIRTUAL_ENV), "")
	@${cmd_pylama}
	@${cmd_mypy}
	@${cmd_isort}
else
	@echo $(fallback_text)
	docker exec -it ${api_name} ${cmd_pylama}
	docker exec -it ${api_name} ${cmd_mypy}
	docker exec -it ${api_name} ${cmd_isort} -c
endif

test:
ifneq ($(VIRTUAL_ENV), "")
	@${cmd_test}
else
	@echo $(fallback_text)
	@docker exec -it ${api_name} ${cmd_test}
endif

migrations:
ifneq ($(VIRTUAL_ENV), "")
	@./manage.py makemigrations
	@./manage.py migrate
	@git add '*/migrations/*.py'
else
	@echo $(fallback_text)
	@docker exec -it ${api_name} ./manage.py makemigrations && ./manage.py migrate
	@git add '*/migrations/*.py'
endif

submodule:
	git submodule update --remote
