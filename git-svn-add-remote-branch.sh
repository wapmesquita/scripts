#!/bin/bash


function usage
{
    echo "usage: git-svn-add-remote-branch.sh OPTIONS "
    echo "Where OPTIONS are:"
    echo "-n | --name"
    echo "             Branch name e.i. reference on git. It is not necessary to be the same name of the branch in SVN"
    echo "-p | --path"
    echo "             Path (URL) of the branch in SVN repository"
    echo "-r | --revision"
    echo "             Revision that the branch was created"
    echo "-h | --help"
    echo "             Show this help"
    echo "Examples: "
    echo "           git-svn-add-remote-branch.sh -n my-branch -p https://svn.my-branch.url/branches/my-svn-branch -r 34235"
}


if [ "$1" == "" ]; then
 usage
 exit 1
fi

while [ "$1" != "" ]; do
    case $1 in
        -n | --name )    shift
                                branch=$1
                                ;;
        -p | --path )           shift
                                svnPath=$1
                                ;;
        -r | --revision )       shift
                                rev=$1
                                ;;
        -h | --help )           usage
                                exit
                                ;;
        * )                     usage
                                exit 1
    esac
    shift
done

if [ "$branch" == "" ]; then
 usage
 exit 1
fi

if [ "$svnPath" == "" ]; then
 usage
 exit 1
fi

if [ "$rev" == "" ]; then
 usage
 exit 1
fi

remote='svn-'$branch

git config --add svn-remote.svn-$remote.url $svnPath
git config --add svn-remote.svn-$remote.fetch :refs/remotes/$remote
git svn fetch $remote -r $rev
git checkout -b $branch $remote
git svn rebase
