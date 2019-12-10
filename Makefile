# for catch input arguments
RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
$(eval $(RUN_ARGS):;@:)

check:
	mypy jibrel && isort **/*.py -vb -q -rc -c | grep ERR
	exit 0

test:
	pytest
	exit 0

start:
	docker-compose up -d

stop:
	docker-compose down

clean:
	docker-compose down -v
	exit 0
