
## Migration from Django user schema to 1flow user schema

    SRC=prod
    #DST=zero
    DST=zero:feature/core+ember

    fab ${SRC} maint
    fab ${DST} maint

    fab ${SRC} sdf.getdata:profiles
    # edit profiles > adapt model (+data, -select_*, …)

    fab ${SRC} sdf.getdata:auth.User
    # NO: edit auth.User > remove 'username'
    # YES: s/auth\.user/base.user/

    # HEADS UP: only if $SRC != $DST
    fab ${SRC} op

    # Will fail at the syncdb run (it's normal)
    fab ${DST} runable

    #
    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
    # restart-from-scratch note:
    #       lxc-scratch-restart.sh (or from Pgadmin3: remove DB)
    #       fab $DST sdf.createdb (or runable, given your context)
    #       from Pgadmin3: restore DB from dump
    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
    #

    # ONLY: if already partially up-to-date (eg. on OBI)
    fab ${DST} command:'echo "yes" | ./manage.py reset base'
    fab ${DST} command:'echo "yes" | ./manage.py reset landing'
    fab ${DST} firstdata

    # Will fail at the syncdb run (it's normal)
    fab ${DST} runable

    fab ${DST} command:'echo "yes" | ./manage.py syncdb'
    fab ${DST} command:'echo "yes" | ./manage.py reset profiles'

    # load the modified data.
    fab ${DST} sdf.putdata:./data/20130605-1flow.io/after/base.User_2013-06-05_0001.json
    fab ${DST} sdf.putdata:./data/20130605-1flow.io/after/profiles_2013-06-05_0001.json

    # Not required, but I had to run these on 'local' and 'obi'.
    #fab ${DST} command:'echo "yes" | ./manage.py reset south'
    #fab ${DST} command:'./manage.py migrate redisboard --fake'

    # In case we must do them one by one.
    # fab ${DST} command:'./manage.py migrate redisboard --fake 0001'
    # fab ${DST} command:'./manage.py migrate redisboard --fake 0002'
    # fab ${DST} command:'./manage.py migrate redisboard --fake 0003'

    # Not required, but I had to run these on 'local' target.
    # fab ${DST} command:'./manage.py migrate djcelery --fake'
    # fab ${DST} command:'./manage.py migrate tastypie --fake'

    #
    # TODO / SYSADMIN: install new server packages (eg. supervisor, MongoDB…)
    #
    # eg.   fab -H ${MAIN_SERVER} sdf.fabfile.db_mongo
    #       vim /etc/mongodb.conf
    #       …
    #

    # HEADS UP: you will need to specify manually all machines,
    # because -R … won't work. Don't ask me why, I don't know.
    fab ${DST} command:'sudo rm /etc/supervisor/conf.d/*'

    fab ${DST} deploy
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
