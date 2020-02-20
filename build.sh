#!/bin/bash
DNS_CLOUDFLARE_IMAGE_TAG=v1.2.0 # get it from https://github.com/certbot-docker/certbot-docker/releases
CERTBOT_NOTIFY_EMAIL=admin@taghub.net

docker build \
  --rm \
  --build-arg version=$DNS_CLOUDFLARE_IMAGE_TAG \
  --build-arg CERTBOT_DOMAINS='[["taghub.io","*.taghub.io"],["smartm.no","*.smartm.no"]]' \
  --build-arg CERTBOT_CF_API_TOKEN=$CF_API_TOKEN_DOCKER_SECRET_NAME \
  --build-arg CERTBOT_NOTIFY_EMAIL=$CERTBOT_NOTIFY_EMAIL \
  --build-arg DOCKER_HOST=tcp://10.244.201.170:4243 \
  --build-arg DOCKER_SWARM_SERVICES=gateway_aws-traefik,gateway_gcp-traefik, \
  --build-arg CERTBOT_BASE_IMAGE=registry.taghub.net:5000/certbot-cf-base:latest \
  --build-arg CERTBOT_RESULT_IMAGE=registry.taghub.net:5000/certbot-cf \
  -t registry.taghub.net:5000/certbot-cf-base .
