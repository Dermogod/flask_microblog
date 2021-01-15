#!/bin/sh

source myvenv/bin/activate

while true; do
    flask db upgrade
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo Upgrade command failed, retrying in 5 seconds.
    sleep 5
done
flask translate compile
exec gunicorn -b :5001 --access-logfile - --error-logfile - microblog:app