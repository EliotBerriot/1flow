#!/bin/bash -e
#
#   run('bash "{0}" install "{1}" "{2}" "{3}" "{4}"'.format(
#                    custom_script, env.environment, env.virtualenv,
#                    role_name, env.host_string))

VENV=$2
INSTALL_FILE="~/.boilerpipe_installed"

case $1 in
    install)

    if [ ! -e $INSTALL_FILE ]; then

        sudo apt-get install -q --yes --force-yes openjdk-7-jre python-jpype

        cat >> ~/.bashrc <<EOF
export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
export PATH=$PATH:$JAVA_HOME
EOF

        cd ${WORKON_HOME}/${VENV}/lib/python2.7/
        ln -sf /usr/lib/python2.7/dist-packages/jpype .
        ln -sf /usr/lib/python2.7/dist-packages/_jpype.so .

        touch ${INSTALL_FILE}
    fi

    rm JPype-*.egg-info

    ln -sf /usr/lib/python2.7/dist-packages/JPype-*.egg-info .

    ;;
    *)

