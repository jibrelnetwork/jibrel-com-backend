cmd_mypy = mypy jibrel
cmd_isort = isort **/*.py -vb -q -rc -c | grep ERR
cmd_test = pytest
api_name = jibrelcom_backend_api_1
minimum_apps = broker main_db redis admin_db s3local
fallback_text = "venv is not activated, starting docker"
params_passed = false

# for catch input arguments
RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
$(eval $(RUN_ARGS):;@:)


start:
ifeq ($(RUN_ARGS), all)
	@echo $(RUN_ARGS)
	@docker-compose up -d
else
	@echo $(RUN_ARGS)
	@docker-compose up -d ${minimum_apps}
endif

stop:
	@docker-compose down

clean:
	@docker-compose down -v

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


test:
ifneq ($(VIRTUAL_ENV), "")
	@${cmd_test}
else
	@echo $(fallback_text)
	@docker exec -it ${api_name} ${cmd_test}
endif

check:
ifneq ($(VIRTUAL_ENV), "")
	@${cmd_mypy}
	@${cmd_isort}
else
	@echo $(fallback_text)
	docker exec -it ${api_name} ${cmd_mypy}
	docker exec -it ${api_name} ${cmd_isort}
endif
