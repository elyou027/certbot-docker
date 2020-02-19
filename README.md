Based on https://hub.docker.com/r/certbot/dns-cloudflare

Fully automated docker image to request and update certificates from Letsencrypt

Currently supporting auth challenges:
* DNS (also wildcard) by Cloudflare provider

Features:
* Can be run on any swarm cluster node
* State (`/etc/letsencrypt`) is saved in docker image that builds every time when certificates updated
  * first run (to get certs) you need to run base image `registry.taghub.net:5000/certbot-cf-base:latest`
  * this image gets certs and build and push docker image `registry.taghub.net:5000/certbot-cf` with `/etc/letsencrypt`
  inside
  * next run image `registry.taghub.net:5000/certbot-cf` 
* Deploy scenarios performs by `CERTBOT_CHALLENGE` and can be extend in future. Currently supported:
  * `swarm-deploy-hook.py` - Deploy and update certificates made via swarm secrets
  * deploy to swarm is disabled by default. So you can safely run this image without updates (for testing)
  * to enable this feature pass `--deploy-to-swarm` as argument to container (look at examples bellow)
* Deploy hook called only when the certificate is created or renewed
* Deploy hook executed each time for each group of certificates. So for 
`'[["test2.taghub.net","*.test2.taghub.net"],["test3.taghub.net"]]'` it will be called twice
* Two secrets are created by deploy hook for each group of certificates:
  * for key file
  * for cert file
  Secrets are created by template: `acme-cert-<domain_from_first_cert>-$DOCKER_SECRET_TAG`
  `DOCKER_SECRET_TAG` can be set manually or it can be calculated automatically by `date.now()`
* Updating service two times is not good, so deploy hook uses event system (by writing a file) to inform that it has been
called and service updated once by the main script `entrypoint.py`
* Updating services are performed by replacing secrets id. File paths and file modes are preserved. Old secrets do 
not removed
* Email alerts can be added easy

Some settings can be set via CLI arguments and all can be set via ENVIRONMENT variables. The last method is preferred 
as more convenient. The best way to set environment variables is to set them when building image

All supported variables can be found in `Dockerfile` https://gitlab.taghub.net/ops/certbot/blob/master/Dockerfile

Some notes about them:
* Always use `CERTBOT_CF_API_TOKEN`. `CERTBOT_CF_API_EMAIL` and `CERTBOT_CF_API_KEY` will be ignored if you set 
`CERTBOT_CF_API_TOKEN`. They are left for backward compatibility
* `CERTBOT_NOTIFY_EMAIL` - set here you a real email that will be used for creating an account on the Let's Encrypt and 
sending emails with alerts about certifications expiration
* `DOCKER_SWARM_SERVICE` - example `gateway_aws-traefik,gateway_gcp-traefik`. Default value is `none`, that means do not
 update any services. Useful to set to `none` for first run to get certs and secrets but without touching any services
* `CERTBOT_DOMAINS` - as certificates can be grouped together to one file, we have to use two-dimensional array. For 
example: `'[["test2.taghub.com","*.test2.taghub.com"]]'`. This variable can be overrided by `--domains` key. 
See examples bellow
* `CERTBOT_BASE_IMAGE` is used as a base to build an image with current `letsencrypt` folder state
* `CERTBOT_RESULT_IMAGE` image that used to get and maintain certificates
 
# How to build the image

## Manually
```
DNS_CLOUDFLARE_IMAGE_TAG=v1.2.0         # get it from https://github.com/certbot-docker/certbot-docker/releases
CERTBOT_CF_API_TOKEN=your CF token      # CF login

docker build \
      --rm
      --build-arg version=$DNS_CLOUDFLARE_IMAGE_TAG \
      --build-arg CERTBOT_DOMAINS='[["test2.taghub.com","*.test2.taghub.com"]]'\
      --build-arg CERTBOT_CF_API_TOKEN=my_cf_token \
      --build-arg CERTBOT_NOTIFY_EMAIL=devops@taghub.net \
      --build-arg DOCKER_HOST=tcp://10.244.201.170:4243 \
      --build-arg DOCKER_SWARM_SERVICES=gateway_aws-traefik,gateway_gcp-traefik, \
      --build-arg CERTBOT_BASE_IMAGE=registry.taghub.net:5000/certbot-cf-base:latest \
      --build-arg CERTBOT_RESULT_IMAGE=registry.taghub.net:5000/certbot-cf \
      -t registry.taghub.net:5000/certbot-cf-base .

# push the image to the registry
docker push registry.taghub.net:5000/certbot-cf-base
```

## CI
Simply run Gitlab pipeline

# How to use the image

## Getting help
```
docker run --rm \
    -e CERTBOT_DOMAINS=$CERTBOT_DOMAINS \
    hub.taghub.net/certbot-dns-cloudflare --help
```

## Some useful keys
* `--deploy-to-swarm` without this key "deploy hook" will not be called
* `--loglevel debug` default loglevel is "INFO"
* `--staging` for testing only. LetsEncrypt has a limitation of the number of certs and calls. 
Using staging you can get unlimited count of fake certs. Useful for testing
* `--domains '[["test2.taghub.net","*.test2.taghub.net"]]'` optional domains arg.  If it is set that it has higher 
precedence against `CERTBOT_DOMAINS` variable

## How to request a new cert

1. Manually edit swarm service by adding secrets first time. 
1.1. You can request certs and create secrets without editing the services if run image with 
`-e DOCKER_SWARM_SERVICES:none`:
```
export CERTBOT_BASE_IMAGE=registry.taghub.net:5000/certbot-cf-base:latest
docker run --rm \
    -e DOCKER_SWARM_SERVICES:none \
    $CERTBOT_BASE_IMAGE \
    --loglevel debug \
    --deploy-to-swarm \
    --domains '[["test2.taghub.net","*.test2.taghub.net"]]' \
    create_new
```
This command creates new image (with state of `/etc/letsencrypt`) that can be used in future instead of 
`$CERTBOT_BASE_IMAGE`
1.2. Next, you need `DOCKER_SECRET_TAG` for the created secrets. These can get from the output of previous command or
from `docker service ls`. For example:
```
docker secret ls
ID                          NAME                                       DRIVER              CREATED             UPDATED
8l0bwejkd7ccc5vgrmv5n1ojl   acme-cert-test2.taghub.net-20200218150900                       20 hours ago        20 hours ago

```
`20200218150900` is `DOCKER_SECRET_TAG`
2. Manually update docker stack yml file with new secrets and apply changes

3.1. Optional, if you want to check all flow you can rerun docker image without `-e DOCKER_SWARM_SERVICES:none` and with
`CERTBOT_BASE_IMAGE` that hasn't got `/ect/letsecnrypt`. This is important because if you rerun with 
`CERTBOT_RESULT_IMAGE` then certificates will not update (too early yet) and deploy hook will not be called. So any 
changes to services will not be made
```
export CERTBOT_BASE_IMAGE=registry.taghub.net:5000/certbot-cf-base:latest
docker run --rm \
    ${CERTBOT_BASE_IMAGE} \
    --loglevel debug \
    --deploy-to-swarm \
    --domains '[["test2.taghub.net","*.test2.taghub.net"]]' \
    create_new
```
4. In future use `CERTBOT_RESULT_IMAGE` to maintain current certificate sets
```
export CERTBOT_RESULT_IMAGE=registry.taghub.net:5000/certbot-cf
docker run --rm \
    ${CERTBOT_RESULT_IMAGE} \
    --loglevel debug \
    --deploy-to-swarm \
    --domains '[["test2.taghub.net","*.test2.taghub.net"]]' \
    create_new
```

## How to renew a cert

The same way as creating. This is very useful that you don't have to change keys for image

## How to remove or add new certs

1. Manually edit swarm service by adding secrets first time. You can create secrets without updating the services if 
run image with `-e DOCKER_SWARM_SERVICES:none`:
```
docker run --rm \
    -e DOCKER_SWARM_SERVICES:none \
    hub.taghub.net/certbot-dns-cloudflare \
    --loglevel debug \
    --deploy-to-swarm \
    --domains '[["test2.taghub.net","*.test2.taghub.net"]]' \
    create_new
```
2. Simple rerun flow:
* first run (to get certs) you need to run base image `registry.taghub.net:5000/certbot-cf-base:latest`
* this image gets certs and create and upload docker image `registry.taghub.net:5000/certbot-cf` with `/etc/letsencrypt`
  inside
* next run image `registry.taghub.net:5000/certbot-cf` 

## Example of stack file

Example of docker stack file can be found here https://gitlab.taghub.net/ops/certbot/blob/master/docker-stack-example.yml
Please look at `version`. It has to be 3.6+