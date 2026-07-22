from django.urls import path
from .views import (
    LoginView,
    PinVerifyView,
    LogoutView,
    MeView,
    TokenRefreshView ,
    ChangePinView,
    ChangePasswordView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('login/verify/', PinVerifyView.as_view(), name='pin_verify'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('change-pin/', ChangePinView.as_view(), name='change_pin'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# 