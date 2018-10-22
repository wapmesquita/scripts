#!/bin/bash -xe

INTELLIJ_VERSION=2018.1.2
OPT_DIR=$HOME/opt/.
# apt-get install open-jdk-9

wget https://download.jetbrains.com/idea/ideaIC-$INTELLIJ_VERSION.tar.gz

tar -zxvf ideaIC-$INTELLIJ_VERSION.tar.gz -C $OPT_DIR

