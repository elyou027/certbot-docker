#!/usr/bin/env python

import json
import argparse
import logging
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import docker
from docker.types import SecretReference
import io


def get_env(env_name, default_val=None):
    return os.environ.get(env_name, default_val)


LETSENCRYPT_PATH = os.path.join(get_env("CERTBOT_DATA_DIR_PATH", "/etc"), "letsencrypt")
LOG = None


def get_logger():
    global LOG
    if not LOG:
        loglevel = get_env("LOGLEVEL", "INFO")
        log_format = '[%(asctime)s]:  %(levelname)-8s:  %(message)s'
        time_format = '%H:%M:%S'
        formatter = logging.Formatter(log_format, datefmt=time_format)

        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.loglevel)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        log = logging.getLogger("certbot")
        log.setLevel(level=numeric_level)
        log.addHandler(ch)
        LOG = log
    return LOG


def get_domains(json_str=None):
    if json_str is None:
        json_str = get_env("CERTBOT_DOMAINS", "[]")
    return json.loads(json_str)


def letsencrypt_folder():
    Path(LETSENCRYPT_PATH).mkdir(parents=True, exist_ok=True)


def create_cf_creds():
    if not os.path.isfile("/cloudflare.ini"):
        with open("/cloudflare.ini", "w") as writer:
            if get_env('CERTBOT_CF_API_TOKEN') == 'none':
                get_logger().debug("Creating /cloudflare.ini with dns_cloudflare_email and dns_cloudflare_api_key")
                writer.writelines([
                    f'dns_cloudflare_email = {get_env("CERTBOT_CF_API_EMAIL")}',
                    f'dns_cloudflare_api_key = {get_env("CERTBOT_CF_API_KEY")}'
                ])
            else:
                get_logger().debug("Creating /cloudflare.ini with dns_cloudflare_api_token")
                writer.write(f'dns_cloudflare_api_token = {get_env("CERTBOT_CF_API_TOKEN")}')
        os.chmod("/cloudflare.ini", 0o600)
    else:
        get_logger().debug("File /cloudflare.ini already exists. Using it")


def update_services():
    if os.path.isfile("/tmp/SERVICE_UPDATE_REQUIRED"):
        get_logger().debug("/tmp/SERVICE_UPDATE_REQUIRED exists")
        client = docker.from_env()
        # TODO Play with filters instead of loop of the var DOCKER_SWARM_SERVICES
        for service_name in get_env("DOCKER_SWARM_SERVICES", '').split(','):
            service = client.services.list(filters={"name": service_name})
            for s in service:
                new_secrets = []
                for current_secret in s.attrs['Spec']['TaskTemplate']['ContainerSpec'].get('Secrets', []):
                    str_new_secret_name = '-'.join(
                        current_secret['SecretName'].split('-')[:-1]) + f'-{get_env("DOCKER_SECRET_TAG")}'

                    try:
                        new_secret_obj = client.secrets.list(filters={"name": str_new_secret_name})[0]
                    except IndexError:
                        get_logger().error(
                            "Count of certs that have been got from LetsEncrypt is less than the count of "
                            "secrets that connected to the services!")
                        sys.exit()
                    new_secret = SecretReference(
                        secret_id=new_secret_obj.id,
                        secret_name=str_new_secret_name,
                        filename=current_secret['File']['Name'],
                        mode=current_secret['File']['Mode']
                    )
                    get_logger().debug(f'Updating service: {s.name} with new secret name: {str_new_secret_name}, '
                                       f'filename: {current_secret["File"]["Name"]}, '
                                       f'secret_id: new_secret_obj.id')
                    new_secrets.append(new_secret)

                s.update(secrets=new_secrets)
                get_logger().info(f"Service {s.name} has been successfully updated with new secrets. New tag is:"
                                  f" {get_env('DOCKER_SECRET_TAG')}")


def create_image():
    """
    Create docker image from CERTBOT_BASE_IMAGE. Copy LETSENCRYPT_PATH to it
    """
    if not os.path.isfile('/tmp/SERVICE_UPDATE_REQUIRED'):
        get_logger().debug("Building images aren't needed because certificates have not been updated")
        return
    client = docker.from_env()

    with open(os.path.join(os.getcwd(), 'Dockerfile'), 'w') as writer:
        writer.writelines(
            [
                f"FROM {get_env('CERTBOT_BASE_IMAGE')}\n",
                f"COPY letsencrypt /etc/letsencrypt\n"
            ]
        )
    with open(os.path.join(os.getcwd(), 'Dockerfile'), 'r') as reader:
        dockerfile = reader.read()

    get_logger().debug(f'Building docker image ')
    get_logger().debug(f'Docker file content: {dockerfile}')

    # Compare buildargs with ARG variables in Dockerfile. They count must be the same
    image = client.images.build(
        path=os.getcwd(),
        tag=get_env('CERTBOT_RESULT_IMAGE'),
        rm=True,
        nocache=True,
        forcerm=True,
        buildargs={
            'CERTBOT_CF_API_EMAIL': get_env('CERTBOT_CF_API_EMAIL'),
            'CERTBOT_CF_API_KEY': get_env('CERTBOT_CF_API_KEY'),
            'CERTBOT_CF_API_TOKEN': get_env('CERTBOT_CF_API_TOKEN'),
            'CERTBOT_NOTIFY_EMAIL': get_env('CERTBOT_NOTIFY_EMAIL'),
            'DOCKER_HOST': get_env('DOCKER_HOST'),
            'DOCKER_SWARM_SERVICES': get_env('DOCKER_SWARM_SERVICES'),
            'CERTBOT_BASE_IMAGE': get_env('CERTBOT_BASE_IMAGE')
        }
    )
    response = [line for line in client.images.push(get_env('CERTBOT_RESULT_IMAGE'), stream=True)]
    for r in response:
        get_logger().debug(json.loads(r))


def create_new_dns_cert(domains_list, args):
    letsencrypt_folder()
    if isinstance(domains_list, list):
        domains = ','.join(map(str, domains_list))
    else:
        domains = domains_list

    if len(domains) == 0:
        print("No domains are specified!. Exiting")
        sys.exit(15)

    certbot_args_optional = []
    if args.test_cert:
        certbot_args_optional.append("--test-cert")
    if args.debug:
        certbot_args_optional.append("--debug")

    if args.deploy_to_swarm:
        certbot_args_optional = certbot_args_optional + ["--deploy-hook", os.environ.get('CERTBOT_CHALLENGE')]

    certbot_args = ["certbot", "certonly"] + certbot_args_optional + [
        "--non-interactive",
        "--agree-tos",
        "-m", get_env('CERTBOT_NOTIFY_EMAIL'),
        "--dns-cloudflare",
        "--dns-cloudflare-credentials", "/cloudflare.ini",
        "--preferred-challenges", "dns-01",
        "-d", domains
    ]
    # print(certbot_args)
    result = subprocess.run(certbot_args)
    if result.returncode > 0:
        get_logger().error(f"Exit code is {result.returncode}")
        sys.exit(result.returncode)


def do_things(args):
    letsencrypt_folder()
    if os.environ.get("DOCKER_SECRET_TAG") == "none":
        os.environ["DOCKER_SECRET_TAG"] = datetime.now().strftime("%Y%m%d%H%M%S")
    if "-" in os.environ.get("DOCKER_SECRET_TAG"):
        get_logger().error("DOCKER_SECRET_TAG variable can not contain \"-\" symbol")
        sys.exit(15)
    for d in get_domains(args.domains):
        get_logger().debug(f"Getting certificate(s) for the domains: {d}")
        create_new_dns_cert(d, args)
    update_services()
    create_image()


def __parse_args(help_f=False):
    parser = argparse.ArgumentParser(description='Certbot wrapper script')
    parser.add_argument("--loglevel", "-l", default="INFO", choices=["debug", "DEBUG", "info", "INFO"])
    parser.add_argument("--domains", "-d", help="json formatted domains string. Grouped by certfile. "
                                                "For example:"
                                                " \"[['domain1.example.com','*.domain1.example.com'],"
                                                "'domain2.example.com']\" - will be created two cert files")

    parser.add_argument("--test-cert", "--staging", help="Use the staging server to obtain or revoke test (invalid) "
                                                         "certificates; equivalent to --server "
                                                         "https://acme-staging-v02.api.letsencrypt.org/directory"
                                                         " (default: False)",
                        action='store_true')
    parser.add_argument("--debug", help="Show tracebacks in case of errors, and allow certbot-auto execution on "
                                        "experimental platforms (default:False)", action='store_true')
    parser.add_argument("--deploy-to-swarm",
                        help="Try to deploy new certs with docker swarm secrets",
                        action='store_true')
    subparsers = parser.add_subparsers(title="commands")

    certbot = subparsers.add_parser('certbot', help='Raw certbot commands')
    create_new = subparsers.add_parser("create_new", help='Create new certificates from preconfigured settings')
    create_new.set_defaults(func=do_things)
    if help_f:
        return parser.print_help()
    else:
        return parser.parse_args()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "certbot":
        args = __parse_args()
        if args.loglevel:
            os.environ["LOGLEVEL"] = args.loglevel
        create_cf_creds()
        args.func(args)

    else:
        args = __parse_args(help_f=True)
