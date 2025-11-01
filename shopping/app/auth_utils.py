# app/auth_utils.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from .models import User
from django.contrib.auth.hashers import check_password

# create a signed token
def create_jwt_for_user(user):
    payload = {
        "user_id": user.id,          # DB PK
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(seconds=getattr(settings, "JWT_EXP_DELTA_SECONDS", 86400))
    }
    token = jwt.encode(payload, getattr(settings, "JWT_SECRET"), algorithm=getattr(settings, "JWT_ALGORITHM", "HS256"))
    # PyJWT v2 returns str; ensure bytes->str for older versions if needed
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

# verify email + password
def authenticate_credentials(email, raw_password):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return None
    if check_password(raw_password, user.password):
        return user
    return None

# decode token
def decode_jwt(token):
    try:
        payload = jwt.decode(token, getattr(settings, "JWT_SECRET"), algorithms=[getattr(settings, "JWT_ALGORITHM")])
        return payload
    except jwt.ExpiredSignatureError:
        raise
    except Exception:
        return None
