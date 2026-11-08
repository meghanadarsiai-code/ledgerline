from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.api_login, name="api_login"),
    path("logout/", views.api_logout, name="api_logout"),
    path("accounts/", views.api_accounts, name="api_accounts"),
    path("accounts/<int:account_id>/statement/", views.api_statement, name="api_statement"),
    path("deposit/", views.api_deposit, name="api_deposit"),
    path("withdraw/", views.api_withdraw, name="api_withdraw"),
    path("transfer/", views.api_transfer, name="api_transfer"),
]