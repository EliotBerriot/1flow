# 1flow — libre information platform

This project is about reading and writing on the web, while keeping your data safe and sharing it with friends and colleagues.

It can be seen as the merge of the most-valuable features of Feedly/Readability (implemented) and Facebook/Twitter/Medium/Digg/Storify/ScoopIT/Flickr (on the way) in one application. Obviously 1flow offers less bells-and-whistles, its main feature being the global integration of all others (and probably the fact that it's libre software). 

It has some similarities with a cloud storage, and could perhaps implement a compatible API.

Your data is stored on your own server (or one mutualized with friends or colleagues). Inter-server communication will be implemented via the GnuPG web of trust.

You'll find a more user-oriented original pitch at http://1flow.io/ and some random technical bits on [my blog][blog].


# Current status

The current implementation is fully usable, for what's done. 

**It's in production on http://1flow.io/ and the early adopters use it since April 2013.** 

1flow takes benefit of continuous integration: new features and bug fixes are pushed very regularly.

As it is my own server and not a company project, I don't offer free accounts. I have limited resources, and there are legal issues – at least in France – that I do not want to deal with. They are completely avoided by using your own 1flow instance.

Nevertheless, project contributors will eventually get an access once we meet IRL and have established a trusted relationship. Note that it is still at my discretion in the end, there is no obligation at all.

I'm currently creating a simple installer to get rid of the complex bits (checkout the `feature/installable` branch, and the `develop` one for up-to-date code and features). It will implement `docker` containers, allowing very easy setups by more people.

If you are interested, get in touch via GitHub, [Twitter](https://twitter.com/Karmak23) or [on IRC][irc].


# License

1flow is released under the GNU Affero GPL v3. See the `COPYING` file for license full text.


# Project management and contact

Public project management (features specification, general planned actions, agile iteration content proposals) happens on Trello, backed with the [IRC channel][irc], video conferences and physical meetups. Issues (bugs) are tracked [on GitHub][ghiss]. These are the authoritative working tools.

Public announcements are broadcasted [on the 1flow tumblr][tumblr] and relayed on the [Twitter feed][twitter].

There is a user support forum at http://1flow.userecho.com/ but it's not used for development at all.

`AUTHORS.md` holds the list of authors and all contributors, a short – and not exhaustive – list of their contributions to the project. **It also contains a list of some of the project needs.**

`CONTRIBUTING.md` explicits developer guidelines and *how* to contribute.

Prior version 0.26, 1flow was a startup project. Long in the past, source code and repository were not suited for FOSS development. Since version 0.26, I consider they are starting to be; with your help, we will enhance them. Please yield anything you find unclear.

Note for developers: this is a `git-flow` repository, we follow the [successful branching model](http://nvie.com/posts/a-successful-git-branching-model/).

Thanks for reading ;-)

  [ghiss]: https://github.com/1flow/1flow
  [blog]: http://oliviercortes.com/category/blog.html
  [twitter]: https://twitter.com/1flow_io
  [tumblr]: http://blog.1flow.io/
  [trello]: https://trello.com/b/lSR7Y6Vi/1flow-features-development
  [irc]: irc://chat.freenode.net/#1flow
