
# 1flow — libre information platform

This project is about reading and writing on the web, while keeping your data safe and sharing it with friends and colleagues.

It can be seen as the merge of the most-valuable features of Feedly/Readability (implemented) and Facebook/Twitter/Medium/Digg/Storify/ScoopIT/Flickr (on the way) in one application, with less bells-and-whistles. 

It has some similarities with a cloud storage, and will perhaps implement one via a compatible API. This point is not yet set.

Your data is stored on your own server, and inter-server communication will be implemented via the GnuPG web of trust.

Read more at http://1flow.io/

## Current status

The current implementation is fully usable and in production on http://1flow.io/.

As it is my own server and not a company project, I won't offer access to anyone there, yet. There are also obvious legal issues that I do not want to deal with, which are completely avoided by using your own 1flow instance. This is simpler for everyone.

I'm currently writing a simple installer to get rid of the complex bits (checkout the `installable` branch, and the `develop` one for up-to-date code and features; this is a `git-flow` repository).

The next architecture iteration will be on `docker`, allowing very easy setups by more people.

If you are interested, get in touch via @Karmak23 or on irc://chat.freenode.net/#1flow .

## License

1flow is released under the GNU Affero GPL v3. Licensing and other information (authors, manifesto, etc) are up-to-date in the `feature/installable` (and develop) branch, which is the content of the next stable release. Sorry for it not being clear in the current master branch, but I just pushed the code to github without any official announcement. This will come as soon as the `installable` branch is merged.
