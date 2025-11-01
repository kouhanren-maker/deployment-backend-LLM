from django.urls import path
from . import views

urlpatterns = [
    # path("reco/<int:user_id>/", views.recommend_historical),
    # path("reco/new/", views.recommend_new),
    path("customer/<int:user_id>/", views.process_customer_data),
    path("customer/<int:user_id>/product/<int:product_id>/", views.user_preference),

    path("api/register/", views.register_view, name="register"),
    path("api/login/", views.login_view, name="login"),
    path("api/admin/list_users/", views.list_users_view, name="list_users"),


    path("merchant/<int:user_id>/user_portrait", views.user_portrait),

    path("api/merchant/report/<int:user_id>", views.generate_merchant_report, name="merchant_report"),

]