# Makefile
.PHONY: test run_server

define IMAGE_NAME
scoring
endef

test:
	docker-compose run --build $(IMAGE_NAME) pytest .

run_server:
	docker-compose up
