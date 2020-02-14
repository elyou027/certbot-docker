Based on https://hub.docker.com/r/certbot/dns-cloudflare
 
# How to build the image
```
IMAGE_TAG=v1.2.0  # get it from https://github.com/certbot-docker/certbot-docker/releases
CF_API_EMAIL=my@example.com    # CF login
CF_API_KEY=key                 # CF API key (general)

docker build --build-arg version=${IMAGE_TAG} \
  --build-arg CF_API_EMAIL=sysadmin@skynix.co \
  --build-arg CF_API_KEY=my_key \
  -t registry.taghub.net:5000/update-certs:${IMAGE_TAG} .

# push the image to the registry
docker push registry.taghub.net:5000/update-certs:${IMAGE_TAG}
```

# How to use request a new cert

```
docker run --rm \
  -v /var/lib/docker/data/letsencrypt:/etc/letsencrypt \
  registry.taghub.net:5000/update-certs:${IMAGE_TAG} \
  certonly --non-interactive --agree-tos \
  -m some-email@gmail.com \
  --dns-cloudflare \
  --dns-cloudflare-credentials /cloudflare.ini \
  --preferred-challenges dns-01 \
  -d taghub.net,*.taghub.net
```

# How to renew a cert
```
docker run --rm -ti \
  -v /var/lib/docker/data/letsencrypt:/etc/letsencrypt \
  registry.taghub.net:5000/update-certs:${IMAGE_TAG} renew
```