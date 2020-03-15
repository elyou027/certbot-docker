#!/usr/bin/env python

import os
import shutil
import yaml
from datetime import datetime
from git import Repo
from git import Actor

if os.environ.get("DOCKER_SECRET_TAG") == "none" or os.environ.get("DOCKER_SECRET_TAG") is None:
    os.environ["DOCKER_SECRET_TAG"] = datetime.now().strftime("%Y%m%d%H%M%S")


def get_env(env_name, default_val=None):
    return os.environ.get(env_name, default_val)


GIT_WORKING_DIR = get_env("GIT_WORKING_DIR", os.path.expanduser("~/git_test"))

if not os.path.isdir(os.path.expanduser("~/.ssh")):
    os.umask(0)
    os.makedirs(os.path.expanduser("~/.ssh"), mode=0o700)

if os.path.isdir(GIT_WORKING_DIR):
    shutil.rmtree(GIT_WORKING_DIR)

repo = Repo.clone_from(get_env("GIT_REPO"), GIT_WORKING_DIR)
# print(repo)
# new_branch = repo.create_head(f'feature-{get_env("DOCKER_SECRET_TAG")}')
# new_branch.checkout()

with open(os.path.join(GIT_WORKING_DIR, 'gateway.yml'), 'r') as f:
    stack_f = yaml.load(f, Loader=yaml.FullLoader)

swarm_services = get_env("DOCKER_SWARM_SERVICES", '').split(',')

fin = open(os.path.join(GIT_WORKING_DIR, 'gateway.yml'), "rt")
data = fin.read()

for service in swarm_services:
    service_o = stack_f["services"].get(service)
    if service_o:
        for secret in service_o.get("secrets"):
            old_secret_name = secret['source']
            new_secret_name = '-'.join(
                        old_secret_name.split('-')[:-1]) + f'-{get_env("DOCKER_SECRET_TAG")}'
            data = data.replace(old_secret_name, new_secret_name)
fin.close()

fin = open(os.path.join(GIT_WORKING_DIR, 'gateway.yml'), "wt")
fin.write(data)
fin.close()

repo.index.add('gateway.yml')
author = Actor("GitLab CI", "ci@taghub.net")
repo.index.commit(f"Updated secrets with new tag: {get_env('DOCKER_SECRET_TAG')}", author=author)
repo.remote().push()
