ARG version=v1.2.0
FROM certbot/dns-cloudflare:${version}

ARG CF_API_EMAIL=email@example.com
ARG CF_API_KEY=cf_api_key
ARG NOTIFY_EMAIL=email@example.com

ENV CF_API_EMAIL    ${CF_API_EMAIL}
ENV CF_API_KEY      ${CF_API_KEY}

RUN echo "dns_cloudflare_email = ${CF_API_EMAIL}" > /cloudflare.ini && \
    echo "dns_cloudflare_api_key = ${CF_API_KEY}" >> /cloudflare.ini && \
    chmod go-rwx /cloudflare.ini

# Uncomment lines below only if you need debug (docker run --rm -ti <image> sh)
# COPY entrypoint.sh /usr/local/bin/entrypoint.sh
# ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
# CMD ["certbot"]