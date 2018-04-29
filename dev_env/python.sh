#!/bin/bash -xe

OPT_DIR=$1
PYCHARM_VERSION=2018.1.2

pip install virtualenv

cd /tmp

wget https://download.jetbrains.com/python/pycharm-community-$PYCHARM_VERSION.tar.gz

tar -zxvf pycharm-community-$PYCHARM_VERSION.tar.gz -C $OPT_DIR
