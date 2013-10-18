

# Principle and features

## Phase 1

- get current URL in location bar
- send it to 1flow
    - via view / form (not pure API) to be able to handle anonymous users like readability does
    - handle user not logged in, and ?next=…
    - make sure the session stays between anonymous and authenticated

- host the extension
    - server-side things needed
    http://developer.chrome.com/extensions/packaging.html
    http://developer.chrome.com/extensions/crx.html
    http://developer.chrome.com/extensions/hosting.html
    http://developer.chrome.com/extensions/autoupdate.html

## Phase 2

preferences:
    'preferences.extensions.chrome'
        - which is a TodoAction()
            - which has the following properties:
                '.action_done'
                '.dont_show_again'
                '.remind_later'
                '.date_remind_later'
            - and methods to help in the views / templates.

- when user in on 1flow, display a notification if he has not the extension installed (and the browser is a target)
    - the extension could do a view/preference toggle call on "action_done"
    - thus, when coming on the web app,
        if browser == chrome and not (dont_show_again or action or
        (remind_later and remind_later_date < today - threshold))

## Phase 3

- signify on the browser side that the current page is already in 1flow.
    - display a 1flow icon in the location bar, next to the favorite star?
    - display something IN the webpage (long term: my snaps)


# Server-side operations

- create new article in user special feed
  - create special feed if not existing
  - create reads (as usual…)

# Open questions

- any user can subscribe to my websnaps
  - ok in "free" mode
  - protected by "restricted" attribute?
    - or do we need a "private" attribute not to show the feed at all.
- this new feed must have a "public" (or hidden/private/…) 1flow URL
  - with a public/hidden/… RSS feed
    - we need to generated RSS feeds (etags, etc) from 1flow feeds.
