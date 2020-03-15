#!/bin/sh

if [ "${SSH_PRIVATE_KEY}" != "none" ] && [ "${SSH_PRIVATE_KEY}none" != "none" ]
then
  eval "$(ssh-agent -s)"
  echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  if [ "${GIT_REPO}" != "none" ]
  then
    ssh-keyscan bitbucket.org >> ~/.ssh/known_hosts
  fi
fi

if [ "$1" = "certbot" ]
then
  shift
  certbot "$@"
elif [ "$1" = 'sh' ]
then
  exec "$@"
elif [ "$1" = "git" ]; then
    /usr/local/bin/git-commit.py
else
  /usr/local/bin/entrypoint.py "$@"
fi