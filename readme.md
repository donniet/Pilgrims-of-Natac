# Pilgrims of Natac

## Setup

Pilgrims of Natan runs on [Google App Engine](https://appengine.google.com/) and requires Python 2.5 or greater. Follow the python [directions](https://code.google.com/appengine/docs/python/gettingstarted/devenvironment.html) to install the app engine SDK.

run dev_appserver.py against the source


    cd /path/to/src
    dev_appserver.py .


Open the app in a browser by visiting http://localhost:8080

## Contributing

The code is using 4 spaces per tab, so set your editor to follow this
standard

If you are using a flavor vi, your settings should look like this


    :set expandtab
    :set tabstop=4
    :set shiftwidth=4
    :set softtabstop=4

## Git 

1) pushing up to git hub:

Please use the following sequence of commands to publish your changes to the "main" github repo:

    git fetch origin
    git rebase remotes/origin/master
    git log

--verify that things look like fast forward updates, and not like a merge --

    git fetch origin

--verify that nothing new was brought down--

    git push orign

You should replace orign and master with the names of your remote and target branch if they are different.
You can see a list of your remotes by running

    git remote

To add a remote run

    git add <remote_name> <repo_path_or_url>

2) Adding changes
You should be careful to avoid adding "build artificats" to the repo. 

Use can use 

    git add -u 

to only add "known files" to the staging area. That will avoiding picking up things like executable files inadvertantly. You can use

    git status -s | grep -P "^\?" | cut -c 4-

to find "new" files. That git doesn't know about yet.

Some of them will be junk, like compiler output, IDE temporary files, etc.

If you add those to the .gitignore file they will be ignored by git.

You can then add the remanining files to the using

    git status -s | grep -P "^\?" | cut -c 4- | xargs git add

3) Links and such

[http://www.kernel.org/pub/software/scm/git/docs/everyday.html](Everyday
GIT with 20 Commands or So)

[http://www-cs-students.stanford.edu/~blynn/gitmagic/ch04.html](Git
Magic)

[http://www.bonsai.com/wiki/howtos/vcs/git_remote_resolve/](Resolving
Git Remote issues)


