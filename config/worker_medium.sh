#!/bin/bash -e
#
#   run('bash "{0}" install "{1}" "{2}" "{3}" "{4}"'.format(
#                    custom_script, env.environment, env.virtualenv,
#                    role_name, env.host_string))

VENV=$2

case $1 in
    preinstall)

        sudo apt-get install -q --yes --force-yes openjdk-7-jdk

        # JAVA_HOME is not needed anymore with latest versions of JPype
        #cat >> ~/.bashrc <<EOF
        #export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
        #export PATH=$PATH:$JAVA_HOME
        #EOF

        # We install jpype here, not in the requirements, to avoid
        # installing the JDK (and fonts and many useless libraries)
        # onto every possible 1flow machine.
        pip install -e git+https://github.com/originell/jpype@master#egg=jpype-dev

        (
            cd ${WORKON_HOME}/${VENV}/src/jpype
            ln -sf src/python/jpype .
            ln -sf src/python/jpypex .
        )
        ;;
    install)
        # NOT needed.
        true
        ;;
    *)
        true
        ;;
esac
