#!/bin/bash

# fail script when command fails and print the commands and arguments
set -xe

export APP_RUN=${APP_RUN:=api}
export LOG_LEVEL=${APP_LOGLEVEL:=critical}

COMMAND=$1
if [[ ! -z "$COMMAND" ]]; then
    shift
fi

git config --global user.email "no-reply@chaoscraft.dev"
git config --global user.name "Chris Cross"
uv run alembic upgrade head

case "$COMMAND" in
worker)
    echo "Pull ollama models"
    curl ${OLLAMA_HOST}/api/pull -d '{"name": "all-minilm:22m"}' &
    curl ${OLLAMA_HOST}/api/pull -d '{"name": "nomic-embed-text"}' &
    echo -e "$SSH_KEY" >~/.ssh/id
    chmod 0600 ~/.ssh/id

    echo "Launching Worker:"
    exec uv run polycode worker start --queues celery,default --loglevel=info $*
    ;;

flower)
    echo "Launching Flower:"
    exec uv run celery -A celery_tasks.worker.app flower --address=${APP_HOST:="0.0.0.0"} --port=${APP_PORT:=5000} $*
    ;;

api)
    echo "Launching API:"
    # needed to allow x-forward of proto and ip so url_for in fastapi returns an https schema'd link
    export FORWARDED_ALLOW_IPS=${FORWARDED_ALLOW_IPS:="*"}
    exec uv run polycode server webhook --host=${APP_HOST:="0.0.0.0"} --port=${APP_PORT:=5000} $*
    ;;

socketio)
    echo "Launching Socketio:"
    # needed to allow x-forward of proto and ip so url_for in fastapi returns an https schema'd link
    export FORWARDED_ALLOW_IPS=${FORWARDED_ALLOW_IPS:="*"}
    exec uv run polycode server socketio --host=${APP_HOST:="0.0.0.0"} --port=${APP_PORT:=5000} $*
    ;;

esac
