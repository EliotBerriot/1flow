
import pprint
import simplejson as json
from oneflow.base.models import User


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• as CSV

for user in User.objects.all():
    try:
        data = json.loads(user.profile.register_request_data)
    except:
        data = {}

    email = user.email[5:] if user.email.startswith('BETA') else user.email
    try:
        print '%s; %s' % (email, data.get('language', '').split(',')[0])
    except:
        pass

# ••••••••••••••••••••••••••••••••••••••••••••••••••••• as (not so) pretty dict

langs = {}

for user in User.objects.all():
    try:
        data = json.loads(user.profile.register_request_data)
    except:
        data = {}

    email = user.email[5:] if user.email.startswith('BETA') else user.email
    try:
        ulang = data.get('language', '').split(',')[0]
    except:
        continue
    else:
        lang = langs.get(ulang, [])
        lang.append(email)
        langs[ulang] = lang

print pprint.pformat(langs)
