#!/bin/bash
SCRIPT_PATH="$( cd "$(dirname "$0")" ; pwd -P )"
SOURCE_PATH=$SCRIPT_PATH/src
PYTHONPATH=$SOURCE_PATH py.test -sxv tests $@
