from functools import wraps
from django.http import JsonResponse
from .auth_utils import decode_jwt
from .models import User

# protect views requires (valid-token) user
def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authorization token required"}, status=401)

        token = auth_header.split(" ")[1]
        try:
            payload = decode_jwt(token)
            user = User.objects.get(id=payload["user_id"])
            request.user = user  # attach user object to request
        except Exception as e:
            return JsonResponse({"error": f"Invalid or expired token: {str(e)}"}, status=401)

        return view_func(request, *args, **kwargs)
    return wrapper

# check if login user is merchant
def merchant_required(view_func):
    @wraps(view_func)
    @jwt_required 
    def wrapper(request, *args, **kwargs):
        if request.user.role != "merchant":
            return JsonResponse({"error": "Merchant permissions required"}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

# for administrator only
def admin_required(view_func):
    @wraps(view_func)
    @jwt_required  # admin check always requires JWT
    def wrapper(request, *args, **kwargs):
        if request.user.role != "admin":
            return JsonResponse({"error": "Admin privileges required"}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
