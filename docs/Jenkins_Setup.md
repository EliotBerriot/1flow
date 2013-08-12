
# Harware / system

    lxc-clone -n ci.1flow.net
    ssh ci
    apt-get install sloccount

    sudo su - jenkins
    ssh-keygen -t dsa

    cat ~/.ssh/id_dsa.pub
    # install it in gitolite

    # for Jenkins can do:
    #       fab -H localhost …
    cat ~/.ssh/id_dsa.pub >> ~/.ssh/authorized_keys

    # if we need to pull a local branch:
    # as user olive:
    cat ~jenkins/.ssh/id_dsa.pub >> ~/.ssh/authorized_keys


    sudo vim /etc/postgres/*/pg_hba.conf

        host all postgres 127.0.0.1/32  peer

