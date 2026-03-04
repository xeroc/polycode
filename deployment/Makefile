.EXPORT_ALL_VARIABLES:
.ONESHELL:

SSH_USER := root
SRC := $(wildcard *.hcl)
TARGET ?= infra
LOAD_ENV_FROM_FILE ?= true
DATE := $(shell date +%Y-%m-%d)

# In the default cause, we load all variables from the $TARGET.env file
# This can be overwritten so we can instead get all variables from the existing
# environment, e.g. when deploying cia CICD/gitops pipelines
ifeq ($(LOAD_ENV_FROM_FILE),true)
include $(TARGET).env
endif

all:

ifndef NOMAD_TOKEN
$(error NOMAD_TOKEN required!)
endif

ifndef VAULT_TOKEN
$(error VAULT_TOKEN required!)
endif

ifndef TARGET
$(error TARGET ['infra'] required!)
endif

%: %.hcl
ifdef DRY_RUN
	nomad job plan $<
else
ifdef VERBOSE
	nomad job run $<
else
	nomad job run -detach $<
endif
endif
