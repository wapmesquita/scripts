#!/bin/bash -xe

OPT_DIR=$1
apt-get install open-jdk-9

wget https://download.jetbrains.com/idea/ideaIC-$INTELLIJ_VERSION.tar.gz

tar -zxvf ideaIC-$INTELLIJ_VERSION.tar.gz -C $OPT_DIR

