#!/usr/bin/env python
import re
import os
import docker
import logging
import argparse
import time

client = docker.from_env()
renewed_domains = os.environ.get("RENEWED_DOMAINS", None)
renewed_lineage = os.environ.get("RENEWED_LINEAGE")
docker_swarm_service = os.environ.get("DOCKER_SWARM_SERVICE")
__logger = None


def get_env(env_name, default_val=None):
    return os.environ.get(env_name, default_val)


def get_logger():
    global __logger
    if not __logger:
        loglevel = get_env("LOGLEVEL", "INFO")
        log_format = '[%(asctime)s]:  %(levelname)-8s:  %(message)s'
        time_format = '%H:%M:%S'
        formatter = logging.Formatter(log_format, datefmt=time_format)

        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.loglevel)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log = logging.getLogger("certbot-deploy-hook")
        log.setLevel(level=numeric_level)
        log.addHandler(ch)
        __logger = log
    return __logger


def secret_create():
    docker_secret_tag = os.environ.get("DOCKER_SECRET_TAG")
    if renewed_domains:
        domains = renewed_domains.split()
    else:
        return

    with open(os.path.join(renewed_lineage, "fullchain.pem"), 'r') as file:
        cert_file = file.read()
    with open(os.path.join(renewed_lineage, "privkey.pem"), 'r') as file:
        key_file = file.read()

    # remove * from secret name
    domain_name = re.sub(r'^\*\.|\*|^\.', '', domains[0])

    secret_cert_name = f'acme-cert-{domain_name}-{docker_secret_tag}'
    secret_key_name = f'acme-key-{domain_name}-{docker_secret_tag}'

    secret_cert = client.secrets.create(
        name=secret_cert_name,
        data=cert_file
    )
    get_logger().info(f"Secret {secret_cert_name} with id: {secret_cert.id} was created")
    secret_key = client.secrets.create(
        name=secret_key_name,
        data=key_file
    )
    get_logger().info(f"Secret {secret_key_name} with id: {secret_cert.id} has been created")
    open("/tmp/SERVICE_UPDATE_REQUIRED", "w+")
    get_logger().debug("Created file /tmp/SERVICE_UPDATE_REQUIRED")
    time.sleep(4)


def __parse_args(help_f=False):
    parser = argparse.ArgumentParser(description='Deploy hook for the swarm cluster. Creates secrets and update '
                                                 'services with new ACME certs')
    parser.add_argument("--loglevel", "-l", default="INFO", choices=["debug", "DEBUG", "info", "INFO"])

    if help_f:
        return parser.print_help()
    else:
        return parser.parse_args()


if __name__ == "__main__":
    args = __parse_args()
    secret_create()
