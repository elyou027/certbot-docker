ARG version=v1.2.0
FROM certbot/dns-cloudflare:${version}

ARG CERTBOT_CF_API_TOKEN=none
ARG CERTBOT_CF_API_EMAIL=cf.admin@gmail.com
ARG CERTBOT_CF_API_KEY=cf_api_key
ARG CERTBOT_DOMAINS=[]
ARG CERTBOT_NOTIFY_EMAIL=super.admin@gmail.com
ARG DOCKER_HOST=tcp://your_docker_host:2376
ARG DOCKER_SWARM_SERVICES=none
ARG CERTBOT_BASE_IMAGE=registry.taghub.net:5000/certbot-cf-base:latest
ARG CERTBOT_RESULT_IMAGE=registry.taghub.net:5000/certbot-cf
ARG CERTBOT_CHALLENGE=/usr/local/bin/swarm-deploy-hook.py

ENV CERTBOT_CF_API_EMAIL    ${CF_API_EMAIL}
ENV CERTBOT_CF_API_KEY      ${CF_API_KEY}
ENV CERTBOT_DOMAINS         ${CERTBOT_DOMAINS}
ENV CERTBOT_CF_API_TOKEN    ${CERTBOT_CF_API_TOKEN}
ENV CERTBOT_DATA_DIR_PATH   /etc
ENV CERTBOT_NOTIFY_EMAIL    ${CERTBOT_NOTIFY_EMAIL}
ENV CERTBOT_BASE_IMAGE      ${CERTBOT_BASE_IMAGE}
ENV CERTBOT_RESULT_IMAGE    ${CERTBOT_RESULT_IMAGE}
ENV DOCKER_HOST             ${DOCKER_HOST}
ENV DOCKER_SWARM_SERVICES    ${DOCKER_SWARM_SERVICES}
ENV DOCKER_SECRET_TAG       none
ENV LOGLEVEL                INFO
ENV CERTBOT_CHALLENGE       ${CERTBOT_CHALLENGE}

WORKDIR $CERTBOT_DATA_DIR_PATH

COPY requirements.txt /
RUN pip install -r /requirements.txt

# Sh script is required to handle raw certbot commands
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY entrypoint.py /usr/local/bin/entrypoint.py
COPY swarm-deploy-hook.py /usr/local/bin/swarm-deploy-hook.py
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["--help"]