#!/bin/sh
# This is needed only for debug

if [ "$1" = "certbot" ]
then
  shift
  certbot "$@"
else
	exec "$@"
fi