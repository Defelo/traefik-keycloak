from os import getenv, environ

AUTH_URL = environ["AUTH_URL"]
TOKEN_URL = environ["TOKEN_URL"]
USERINFO_URL = environ["USERINFO_URL"]

CLIENT_ID = environ["CLIENT_ID"]
CLIENT_SECRET = environ["CLIENT_SECRET"]

HOST = getenv("HOST", "0.0.0.0")  # noqa: S104
PORT = int(getenv("PORT", "80"))

REDIS_HOST = getenv("REDIS_HOST", "redis")
REDIS_PORT = int(getenv("REDIS_PORT", "6379"))
REDIS_DB = int(getenv("REDIS_DB", "0"))

OK_TTL = int(getenv("OK_TTL", "60"))
FORBIDDEN_TTL = int(getenv("FORBIDDEN_TTL", "10"))
