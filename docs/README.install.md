
# Bootstrap 1flow project

WARNING: this is about a **development** environment only. For preview / production,
things change a little (services must be installed by hand, etc).

## Pre-installation

You must have `sparks` and my hacked version of `Fabric` to run `1flow`:

    sudo pip install -e git+https://github.com/Karmak23/fabric.git#egg=Fabric
    sudo pip install -e git+https://github.com/Karmak23/sparks.git#egg=sparks

Then, check that your `~/.bashrc` or `~/.profile` runs fully in non-interactive mode.
Fabric and sparks need to access variables that are generaly set in your profile:
historically we met problems with Ubuntu 13.04 default `~/.bashrc` exiting at
start and not running virtualenvwrapper stuff, on which sparks relies.

## Setup 1flow environment

Let Fabric and sparks install Django and all the rest:

    git clone git@dev.1flow.net:1flow.git
    cd 1flow
    fab local firstdeploy
