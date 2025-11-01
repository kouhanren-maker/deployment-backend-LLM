# app/admin.py
# from django.http import JsonResponse
# from .models import User
# from .auth_decorators import admin_required

# @admin_required
# def list_all_users(request):
#     users = User.objects.all().values("id", "email", "role", "create_time")
#     return JsonResponse({"users": list(users)}, safe=False)
