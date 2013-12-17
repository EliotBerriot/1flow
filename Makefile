
bootstrap:
	# like runable, but with the manual minimum for Fabric calls to succeed.
	pip install -r config/dev-requirements.txt
	fab -H localhost local sdf.fabfile.dev_django_full
	sudo chown -R `whoami`: ~/.virtualenvs/1flow
	fab local runable

runable:
	fab local runable

fullrunable:
	fab test runable
	fab prod runable

#runapp:
#	SPARKS_DJANGO_SETTINGS=chani_app ./manage.py runserver 0.0.0.0:8000

compass:
	(cd oneflow/core/static; compass watch)

run:
	honcho -f Procfile.development start --quiet flower,shell,celery_beat

runweb:
	honcho -f Procfile.development start web

runworkers:
	honcho -f Procfile.development start flower celery_beat --quiet flower,celery_beat

	#,worker_high,worker_medium,worker_low,worker_fetch,worker_background,worker_swarm,worker_clean

runshell:
	honcho -f Procfile.development --quiet shell start shell

clean:
	ps ax | grep manage.py | grep -v grep | awk '{print $$1}' | xargs kill -9

purge:
	./manage.py celery purge

test:
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

allfixtures: datafixtures fixtures

datafixtures:
	@find . -name '*.json' -path '*/data/*'

fixtures:
	@find . -name '*.json' -path '*/fixtures/*'

test-restart:
	fab test sdf.restart_services

prod-restart:
	fab prod sdf.restart_services

test-fastdeploy:
	fab test fastdeploy

prod-fastdeploy:
	fab prod fastdeploy
