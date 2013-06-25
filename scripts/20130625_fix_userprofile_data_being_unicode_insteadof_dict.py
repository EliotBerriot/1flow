
from oneflow.profiles.models import UserProfile
import ast

for p in UserProfile.objects.all():
    if type(p.data) == type(u''):
        p.data = {}

    if type(p.register_request_data) == type(u''):
        p.register_request_data = ast.literal_eval(p.register_request_data)

    p.save()
