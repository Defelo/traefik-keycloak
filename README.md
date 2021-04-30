<p>
  
  [![CI](https://github.com/Defelo/traefik-keycloak/actions/workflows/ci.yml/badge.svg)](https://github.com/Defelo/traefik-keycloak/actions/workflows/ci.yml)
  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
  [![DockerHub - traefik-keycloak](https://img.shields.io/docker/pulls/defelo/traefik-keycloak?style=flat-square&label=DockerHub%20-%20traefik-keycloak)](https://hub.docker.com/r/defelo/traefik-keycloak)

</p>

# traefik-keycloak

Keycloak Integration for Traefik

## Setup Instructions

### Keycloak
1. Create a new `openid-connect` client in Keycloak
2. Set `Access Type` to `confidential`
3. Create Redirect URIs for your services (`https://<DOMAIN>/_oauth`)
4. Copy secret from `Credentials` tab
5. Go to `Mappers` tab and add a builtin `client roles` mapper:
    - Set `Client ID` to the id of your client
    - Set `Token Claim Name` to `roles`
    - Disable `Add to access token`
    - Enable `Add to userinfo`
    - Save
6. Create roles for your services

### traefik-keycloak.env
1. Replace `<DOMAIN>` and `<REALM>` placeholders in `AUTH_URL`, `TOKEN_URL` and `USERINFO_URL`
2. Set `CLIENT_ID` to your client id and `CLIENT_SECRET` to your client secret
3. (*optional*) Adjust `OK_TTL` and `FORBIDDEN_TTL`

### Service Container
1. Add a new label to define the auth middleware and point it to your traefik-keycloak container:
    ```
    traefik.http.middlewares.service-auth.forwardauth.address: http://traefik-keycloak/service
    ```
    The path of this address has to match the name of a role in Keycloak. Access is granted if and only if the user is a member of this role.
2. (*optional*) Add a `oauth_path` query parameter to change the callback path to which Keycloak will redirect (default is `/_oauth`). If you do this, you also have to adjust your Redirect URI in Keycloak.
3. Add a label to use this middleware in your traefik router:
    ```
    traefik.http.routers.service.middlewares: service-auth
    ```
