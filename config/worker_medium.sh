#!/bin/bash -e
#
#   run('bash "{0}" install "{1}" "{2}" "{3}" "{4}"'.format(
#                    custom_script, env.environment, env.virtualenv,
#                    role_name, env.host_string))

VENV=$3

case $1 in
    preinstall)
        #
        # NOTE: as of 2013-07-11, this script is no longer needed
        #       because we use a full-python stack again. I keep it
        #       here for memories if we ever need to create another
        #       again: it will be simpler to start from this one
        #       than from nothing.
        #
        # We use it to clean the system from now-obsolete packages.
        #


        sudo apt-get remove --purge -q --yes --force-yes openjdk-7-jdk || true

        # JAVA_HOME is not needed anymore with latest versions of JPype
        #
        #cat >> ~/.bashrc <<EOF
        #export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
        #export PATH=$PATH:$JAVA_HOME
        #EOF
        #
        # BUT STILL, some of the BoilerPipe dependancies need it,
        # thus I have put it in ~/.env.

        # We install jpype here, not in the requirements, to avoid
        # installing the JDK (and fonts and many useless libraries)
        # onto every possible 1flow machine.
        #pip install -e git+https://github.com/originell/jpype@master#egg=jpype-dev

        # (
        #     cd ${WORKON_HOME}/${VENV}/src/jpype
        #     ln -sf src/python/jpype .
        #     ln -sf src/python/jpypex .
        # )

        yes | pip uninstall jpype boilerpipe || true

        ;;
    install)
        # NOT needed.
        true
        ;;
    *)
        true
        ;;
esac
