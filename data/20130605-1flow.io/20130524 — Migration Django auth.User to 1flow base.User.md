
## Migration from Django user schema to 1flow user schema

    SRC=prod
    DST=zero

    fab ${SRC} maint

    fab ${SRC} sdf.getdata:profiles
    # edit profiles > adapt model (+data, -select_*, …)

    fab ${SRC} sdf.getdata:auth.User
    # NO: edit auth.User > remove 'username'
    # YES: s/auth\.user/base.user/

    # Will fail at the syncdb run (it's normal)
    fab ${DST} runable

    fab ${DST} command:'./manage.py syncdb'
    fab ${DST} command:'./manage.py reset profiles'

    fab ${DST} sdf.putdata:
        # modified auth.User
    fab ${DST} sdf.putdata:
        # modified profiles

    fab ${DST} command:'./manage.py reset south'
    fab ${DST} command:'./manage.py migrate redisboard --fake 0001'
    fab ${DST} command:'./manage.py migrate redisboard --fake 0002'
    fab ${DST} command:'./manage.py migrate redisboard --fake 0003'

    fab ${DST} command:'sudo rm /etc/supervisor/conf.d/*'
    fab ${DST} deploy
    fab ${DST} command:'sudo supervisorctl reload'

    # NOT NEEDED:
    #fab ${DST} sdf.update_services_configuration
    #fab ${DST} sdf.restart_services

    fab ${DST} op

## Form adaptations for a User without `username` attribute

As of 20130604, we decided to keep the `username` attribute for @coolness sake. But refering to sparks.django.models.EmailUser, the following content is what
I studied/did to implement it.

cf. https://docs.djangoproject.com/en/1.5/topics/auth/customizing/#custom-users-and-the-built-in-auth-forms


### Need rewrite

- UserCreationForm
- UserChangeForm

### OK or should be OK

- PasswordResetForm: should be OK
- SetPasswordForm: OK
- AuthenticationForm: OK
- PasswordChangeForm: OK
- AdminPasswordChangeForm: OK

## Implementation / Tests

- sparks create superuser [OK]
- inscription [OK]
    - delay 1 second > still problems with the inlined profile
- re-inscription [OK]
- classic admin, list + form [OK]
- admin 1flow, list + form [OK]
    - change password [OK]
- admin création [OK]
- edit profile [OK]
- change password [OK]
