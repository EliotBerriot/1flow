
# Harware / system

    lxc-clone -n ci.1flow.net
    ssh ci
    apt-get install
    sudo su - jenkins
    ssh-keygen -t dsa

    cat ~/.ssh/id_dsa.pub
    # install it in gitolite

    cat ~/.ssh/id_dsa.pub >> ~/.ssh/authorized_keys
