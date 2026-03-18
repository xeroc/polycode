VERSION := $(shell date +%Y%m%d%H%M)

docker_build:
	docker build -t ghcr.io/xeroc/polycode:$(VERSION) .

docker_push:
	docker push ghcr.io/xeroc/polycode:$(VERSION)

docker: docker_build docker_push
