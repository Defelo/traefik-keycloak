FROM python:3.9-alpine AS builder

RUN apk add --no-cache \
    build-base~=0.5 \
    gcc~=10.3 \
    musl-dev~=1.2 \
    libffi-dev~=3.3

WORKDIR /build

RUN pip install pipenv==2020.11.15

COPY Pipfile /build/
COPY Pipfile.lock /build/

ARG PIPENV_NOSPIN=true
ARG PIPENV_VENV_IN_PROJECT=true
RUN pipenv install --deploy --ignore-pipfile


FROM python:3.9-alpine

LABEL org.opencontainers.image.source="https://github.com/Defelo/traefik-keycloak"

WORKDIR /app

RUN set -x \
    && addgroup -g 1000 api \
    && adduser -G api -u 1000 -s /bin/bash -D -H api \
    && mkdir /app/data \
    && chown api:api /app/data

USER api

EXPOSE 8080

COPY --from=builder /build/.venv/lib /usr/local/lib

COPY api.sh /app/
COPY api /app/api/

ENTRYPOINT /app/api.sh
