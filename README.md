


# 1flow — libre information platform

This project is about reading and writing on the web, while keeping your data safe and sharing it with friends and colleagues.

It can be seen as the merge of the most-valuable features of Feedly/Readability (implemented) and Facebook/Twitter/Medium/Digg/Storify/ScoopIT/Flickr (on the way) in one application. Obviously 1flow offers less bells-and-whistles, its main feature being the global integration of all others (and probably the fact that it's libre software).

It has some similarities with a cloud storage, and could perhaps implement a compatible API.

Your data is stored on your own server (or one mutualized with friends or colleagues). Inter-server communication will be implemented via [the GnuPG web of trust][kgpg].

You'll find a more user-oriented original pitch at http://1flow.io/ and project news [on the official blog][1blog].

1flow development is [funded via Gittip][gittip].



# Quick installation

1flow can be run on a single machine, but it is more likely to be installed on a multi-machines setup, when in production.

If you plan to install it on your machine for development or test purposes, know that this process will install `PostgreSQL`, `MongoDB`, `Redis` and `memcache` and their development packages. A lot more will be installed too, but most of it will be in the `virtualenv`, thus not particularly polluting your machine.

The best option is to run the installation process on a dedicated (probably virtual) machine or in an LXC container.



## Linux

This installation has been tested on Ubuntu 12.04 LTS and 13.10.

I've written it by memory, please [open an issue](issues/new) in case you find anything unclear or incomplete.

We assume you already have a development environment installed, with `git` and `pip`.

    # sparks (1flow's deployment library) needs virtualenvwrapper to be installed
    sudo pip install virtualenvwrapper
    mkvirtualenv 1flow
    workon 1flow
    # A lot of things in sparks and 1flow rely on the ~/sources/ directory.
    cd && mkdir sources && cd sources
    git clone git+https://github.com/1flow/1flow.git
    cd 1flow
    cp config/dot.env.example ~/.env.1flow

    make bootstrap

During the bootstrap phase, which *will* take a long time, you have to:

- tune `~/.env.1flow` to match your environment. It's nearly already set for
  a development environment on 127.0.0.1. You will not have many things to
  change if running on localhost, but it's still worth a review.
- Create the PostgreSQL role `oneflow_admin` with the password you set
  in `~/.env.1flow`. Grant it `CREATE DATABASE` and `CREATE ROLE`
  (`INHERIT` is not needed).
- under Linux only: create a database and a PG role for your Linux user account. Eg.

    sudo su - postgres
    createuser YOUR_USERNAME
    # and set it superuser
    createdb YOUR_USERNAME -o YOUR_USERNAME
    exit

- tune `/etc/postgresql/…/pg_hba.conf` to allow yourself to connect via `peer`, and other accounts to connect via `md5`.

Notes:

- as `make bootstrap` will install PostgreSQL, wait a little if it's not installed when you try to create the `oneflow_admin` role.
- you can run `make bootstrap` as many times as necessary if you miss any manual step.

When the `bootstrap` procedure is acheived, you can run 1flow:

	. ~/.env.1flow
    make run

Then go to http://localhost:8000/ and enjoy your local 1flow instance.

You can put it behind an `nginx` proxy if you want.



### And after…

To run a production instance, things are *not* much complicated. You will have to tune the project `fabfile` to suit your needs, and use fabric/sparks commands. If you're curious, the `production` target is the one that powers [1flow.io](http://1flow.io/).



## Install on OSX

1flow runs perfectly on OSX Mavericks (10.9) with Xcode 5.x.

Previously, I developed 1flow on OSX 10.8 with Xcode 4.6 and it worked completely fine too. I haven't tested it recently, but it should still work. Please report any issue you find.

Just follow the same procedure as for a Linux installation.



### Caveats on OSX

If you run `make bootstrap` more than once, you could eventually end up in a situation where one or more service (MongoDB, PostgreSQL, Redis, Memcached) is installed but not launched. This happens because the related `.plist` is not symlinked to `~/Library/LaunchAgents/`. Just run something like:

    ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents
    lunchy start postgres

[Lunchy](lunch) has been installed by `sparks`, I'm sure you will love it.



## Future plans

I'm thinking about creating a `docker` container to get a development environment already setup in one command. Checkout the `feature/installable` branch for up-to-date code and documentation of this task.

If you are interested in helping out, I will be glad to hear from you and help. Please get in touch via [Twitter](https://twitter.com/Karmak23) or [IRC][irc].



# Current status

The current implementation is fully usable, for what's done.

**It's in production on [1flow.io](http://1flow.io/) and the early adopters use it since April 2013.**

1flow takes benefit of continuous integration: new features and bug fixes are pushed very regularly.

As [1flow.io](http://1flow.io/) is my currently my personal server and not a company project, you won't get a free account there. I have limited resources, and there are legal issues – at least in France – that I do not want to deal with, and which are completely avoided by using your own 1flow instance.

Nevertheless, project contributors will eventually get an access once we meet IRL and have established a trusted relationship. Note that it is still at my discretion in the end.



# License

1flow is released under the GNU Affero GPL v3. See the `COPYING` file for details.



# Project management and contact

Public project management (features specification, general planned actions, agile iteration content proposals) [happens on Trello][trello], backed with the [IRC channel][irc], video conferences and physical meetups. Issues (bugs) are tracked [on GitHub][ghiss]. These are the authoritative working tools.

Public announcements are broadcasted [on the 1flow tumblr][tumblr] and automatically relayed on the [Twitter feed][twitter], where sporadic news and small status updates are posted.

There is a user support forum at http://1flow.userecho.com/ but it's not used for development at all.

`AUTHORS.md` holds the list of authors and all contributors, a short – and not exhaustive – list of their contributions to the project. **It also contains a list of some of the project needs.**

`CONTRIBUTING.md` explicits developer guidelines and *how* to contribute.

Prior version 0.26, 1flow was a startup project. Since version 0.26, I consider the code suited for FOSS development, but I could have missed some pieces. Please yield anything you find unclear.

Note for developers: this is a `git-flow` repository, we follow the [successful branching model](http://nvie.com/posts/a-successful-git-branching-model/).

Thanks for reading ;-)


  [lunch]: https://github.com/mperham/lunchy
  [gittip]: https://gittip.com/1flow/
  [ghiss]: https://github.com/1flow/1flow
  [1blog]: http://blog.1flow.io/
  [kgpg]: http://oliviercortes.com/principles-human-trusted-machines-distributed-network.html
  [twitter]: https://twitter.com/1flow_io
  [tumblr]: http://blog.1flow.io/
  [trello]: https://trello.com/b/lSR7Y6Vi/1flow-features-development
  [irc]: irc://chat.freenode.net/#1flow
