#!/bin/sh
# This is needed only for debug

if [ "$1" = "certbot" ]
then
  shift
  certbot "$@"
elif [ "$1" = 'sh' ]
then
  exec "$@"
else
  /usr/local/bin/entrypoint.py "$@"
fi