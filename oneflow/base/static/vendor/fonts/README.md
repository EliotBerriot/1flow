
# How to get the Google fonts locally

- go to http://www.google.com/fonts
- search, and put the font you want **in your collection**
- click the down-arrow in the top-right of the page, download the .ZIP
    - NOTE: The .ZIP is not present if you didn't put the font in your collection
- extract the zip somewhere, for me it's in a subdir next to this `README`
- On google fonts, click "USE" in the bottom-right,
- check the slants you want,
- scroll down, copy the http://fonts.googleapis.com/css?family=... in your browser URL bar,
    - keep this URL handy for the last step (see below),
- copy the raw CSS, put it in a file near the .TTF files


# Convert the .TTF to .WOFF

- on Ubuntu, install `woff-tools`,
- go to your fonts folder,
- run `for f in *.ttf; do sfnt2woff "$f"; done`


# Patch the CSS with static paths

- edit the .CSS you created,
- replace every `http://...googlecontent.com/...` with your static path.

Look at the `Lato` and `Open Sans` examples just here.


# Optional: put the font in 1flow

- Open `core/static/base_header.html`
- look for how it's done for `Lato` and `Open Sans`,
- you need the full URL from Google, for the `WEB_CNDS_ENABLED` part, to get the font from the CDNs.
- Put the path of your local CSS, for the pure-local usage (no CDNs)
