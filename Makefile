runable:
	fab local runable

fullrunable:
	fab test runable
	fab prod runable

test-fastdeploy:
	fab test fastdeploy

prod-fastdeploy:
	fab prod fastdeploy

#runapp:
#	SPARKS_DJANGO_SETTINGS=chani_app ./manage.py runserver 0.0.0.0:8000

runserver:
	honcho -f Procfile.development start

run: runserver

test: tests

tests:
	# REUSE fails with
	# "AttributeError: 'DatabaseCreation' object has no attribute '_rollback_works'"
	# until https://github.com/jbalogh/django-nose/pull/101 is merged.
	#REUSE_DB=1 ./manage.py test oneflow  --noinput --stop
	./manage.py test oneflow --noinput --stop

shell:
	./manage.py shell

#shellapp:
#	SPARKS_DJANGO_SETTINGS=chani_app ./manage.py shell

messages:
	fab local sdf.makemessages

compilemessages:
	fab local sdf.compilemessages

upgrade-requirements:
	(cd config && pip-review -vai)

update-requirements:
	(cd config && pip-dump)

requirements:
	fab local sdf.requirements

syncdb:
	fab local sdf.syncdb
	fab local sdf.migrate

test-restart:
	fab test sdf.restart_services

prod-restart:
	fab prod sdf.restart_services

allfixtures: datafixtures fixtures

datafixtures:
	@find . -name '*.json' -path '*/data/*'

fixtures:
	@find . -name '*.json' -path '*/fixtures/*'
