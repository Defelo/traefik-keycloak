from secrets import token_urlsafe
from typing import Optional
from urllib.parse import urljoin, urlencode, parse_qs, urlparse

import uvicorn
from aiohttp import ClientSession
from aioredis import Redis, create_redis_pool
from fastapi import FastAPI, HTTPException, Response
from fastapi.params import Header, Cookie
from fastapi.responses import RedirectResponse

from environment import AUTH_URL, TOKEN_URL, USERINFO_URL
from environment import REDIS_HOST, REDIS_PORT, REDIS_DB
from environment import CLIENT_ID, CLIENT_SECRET
from environment import HOST, PORT
from environment import OK_TTL, FORBIDDEN_TTL

app = FastAPI()

redis: Optional[Redis] = None


def parse_query(qs: str) -> dict:
    return {k: (v[0] if isinstance(v, list) and len(v) == 1 else v) for k, v in parse_qs(qs).items()}


def parse_url(url: str) -> tuple[str, dict]:
    out = urlparse(url)
    return out.path, parse_query(out.query)


@app.on_event("startup")
async def on_startup():
    global redis
    redis = await create_redis_pool(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}", encoding="utf-8")


async def refresh_access_token(state: str) -> Optional[str]:
    if not (refresh_token := await redis.get(f"refresh_token:{state}")):
        return None

    async with ClientSession() as session, session.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    ) as response:
        if not response.ok:
            return None

        response = await response.json()

    access_token = response["access_token"]
    refresh_token = response["refresh_token"]
    await redis.setex(f"access_token:{state}", response["expires_in"], access_token)
    await redis.setex(f"refresh_token:{state}", response["refresh_expires_in"], refresh_token)

    return access_token


async def get_userinfo(state: str) -> Optional[dict]:
    async def request(token: str):
        async with ClientSession() as session, session.get(
            USERINFO_URL, headers={"Authorization": f"Bearer {token}"}
        ) as resp:
            if resp.ok:
                return await resp.json()

    if access_token := await redis.get(f"access_token:{state}"):
        if response := await request(access_token):
            return response

    if access_token := await refresh_access_token(state):
        if response := await request(access_token):
            return response

    return None


@app.get("/{role}")
async def auth(
    role: str,
    state: Optional[str] = Cookie(None, alias="_oauth_session"),
    protocol: str = Header(..., alias="X-Forwarded-Proto"),
    host: str = Header(..., alias="X-Forwarded-Host"),
    request_uri: str = Header(..., alias="X-Forwarded-Uri"),
    oauth_path: str = "/_oauth",
):
    path, params = parse_url(request_uri)
    if path == oauth_path:
        state = token_urlsafe(64)

        redirect_uri: str = params.get("state")
        code: str = params.get("code")
        if not redirect_uri or not code:
            raise HTTPException(400)

        async with ClientSession() as session, session.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": urljoin(redirect_uri, oauth_path),
            },
        ) as response:
            if not response.ok:
                raise HTTPException(401)

            response = await response.json()

        access_token = response["access_token"]
        refresh_token = response["refresh_token"]
        await redis.setex(f"access_token:{state}", response["expires_in"], access_token)
        await redis.setex(f"refresh_token:{state}", response["refresh_expires_in"], refresh_token)

        user_info: Optional[dict] = await get_userinfo(state)
        if not user_info:
            raise HTTPException(401)

        if role in user_info.get("roles", []):
            await redis.setex(f"ok:{state}", OK_TTL, 1)
        else:
            await redis.setex(f"forbidden:{state}", FORBIDDEN_TTL, 1)

        response = RedirectResponse(redirect_uri)
        response.set_cookie("_oauth_session", state, httponly=True)
        return response

    if state:
        if await redis.get(f"forbidden:{state}") == "1":
            return Response("403 Forbidden", 403)
        if await redis.get(f"ok:{state}") == "1":
            return {"ok": True}

        user_info: Optional[dict] = await get_userinfo(state)
        if user_info:
            if role in user_info.get("roles", []):
                await redis.setex(f"ok:{state}", OK_TTL, 1)
                return {"ok": True}

            await redis.setex(f"forbidden:{state}", FORBIDDEN_TTL, 1)
            return Response("403 Forbidden", 403)

    redirect_uri: str = urljoin(protocol + "://" + host, request_uri)

    return RedirectResponse(
        AUTH_URL
        + "?"
        + urlencode(
            {
                "client_id": CLIENT_ID,
                "redirect_uri": urljoin(redirect_uri, oauth_path),
                "response_type": "code",
                "scope": "openid",
                "state": redirect_uri,
            }
        )
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host=HOST, port=PORT)
