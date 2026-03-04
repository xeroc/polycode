#!/bin/bash

# fail script when command fails and print the commands and arguments
set -xe

export APP_RUN=${APP_RUN:=api}
export LOG_LEVEL=${APP_LOGLEVEL:=critical}

# needed to allow x-forward of proto and ip so url_for in fastapi returns an https schema'd link
export FORWARDED_ALLOW_IPS=${FORWARDED_ALLOW_IPS:="*"}

COMMAND=$1
if [[ ! -z "$COMMAND" ]]; then
    shift
fi

case "$COMMAND" in
worker)
    echo "Launching Worker:"
    exec uv run celery -A celery_tasks.worker.app worker -Ofair --task-events --queues celery,default --loglevel=info $*
    ;;

flower)
    echo "Launching Flower:"
    exec uv run celery -A celery_tasks.worker.app flower --address=${APP_HOST:="0.0.0.0"} --port=${APP_PORT:=5000} $*
    ;;

api)
    echo "Launching API:"
    exec uv run webhook-server webhook --host=${APP_HOST:="0.0.0.0"} --port=${APP_PORT:=5000} $*
    ;;

esac
