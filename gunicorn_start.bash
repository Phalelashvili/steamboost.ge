#!/bin/bash

NAME="MT"                                           # Name of the application
DJANGODIR=/home/MT/src                              # Django project directory
SOCKFILE=/home/MT/run/gunicorn.sock                 # we will communicte using this unix socket
USER=root                                           # the user to run as
GROUP=root                                          # the group to run as
NUM_WORKERS=20                                      # how many worker processes should Gunicorn spawn
DJANGO_SETTINGS_MODULE=base.settings                # which settings file should Django use
DJANGO_WSGI_MODULE=base.wsgi                        # WSGI module name
echo "Starting $NAME as `whoami`"

# Activate the virtual environment

cd $DJANGODIR
source /home/MT/bin/activate
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Create the run directory if it doesn't exist

RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

echo "set botInUse False" | redis-cli
echo "set emoneyInUse False" | redis-cli
echo "set pizzaNotifierStarted False" | redis-cli

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)

exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --timeout 120 \
  --user=$USER --group=$GROUP \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=-
  --preload
