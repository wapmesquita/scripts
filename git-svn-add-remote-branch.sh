#!/bin/bash

git config --add svn-remote.svn-$1.url $2
git config --add svn-remote.svn-$1.fetch :refs/remotes/svn-$1
git svn fetch svn-$1 -r $3
git checkout -b local-$1 svn-$1
git svn rebase
