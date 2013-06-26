# -*- coding: utf-8 -*-
# Settings for worbi.1flow.net (preview worker) and florbi (flower instance),
# hosted on the same machine (thus, same settings, thanks to sparks).

from sparks.django.settings import clone_settings

clone_settings('chani', __file__, globals())
SITE_DOMAIN = 'dev1.1flow.io'
#SITE_DOMAIN = 'dev2.1flow.io'
#EMAIL_HOST = 'gurney'


#GOOGLE_CONSUMER_KEY          =     'dev1.1flow.io'
#GOOGLE_CONSUMER_SECRET       =  'w78SFaBLwwolPWybAsAGkclr'

#GOOGLE_CONSUMER_KEY          =   'dev2.1flow.io'
#GOOGLE_CONSUMER_SECRET       =  '--EzJz4m8H2DX8ma5_YDLfIM'


#Dev1

GOOGLE_OAUTH2_CLIENT_ID      = '494350410052-5cgau95ek6dvhnu0c1tov8j9f10b02ou.apps.googleusercontent.com' # NOQA
GOOGLE_OAUTH2_CLIENT_SECRET  = 'qwribFAXXLHPY4_vtR-nkpFz'


#dev2

#GOOGLE_OAUTH2_CLIENT_ID      = '494350410052-kccc59ku23u9rs9bphh2pfbkabu1lihd.apps.googleusercontent.com' # NOQA
#GOOGLE_OAUTH2_CLIENT_SECRET  = 'KCjXlE9df6YiS_cZMekfh6TB'
