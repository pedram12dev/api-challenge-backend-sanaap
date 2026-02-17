from datetime import timedelta

from config.env import env

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        seconds=env.int("JWT_ACCESS_LIFETIME_SECONDS", default=60 * 60)  # 1 hour
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        seconds=env.int("JWT_REFRESH_LIFETIME_SECONDS", default=60 * 60 * 24 * 7)  # 7 days
    ),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}