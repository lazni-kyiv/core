import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken, AuthenticationFailed

from .models import ActiveToken, LoginLog
from .tokens import PreAuthToken
from .serializers import LoginSerializer, UserSerializer
from user_agents import parse
print("AUTH VIEWS LOADED")
# =========================
# HELPERS
# =========================
def get_device_info(request):
    ua_string = request.META.get("HTTP_USER_AGENT", "")
    ua = parse(ua_string)

    return {
        "user_agent": ua_string,
        "device_name": ua.device.family,
        "browser": ua.browser.family,
        "os": ua.os.family,
    }

def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def set_auth_cookies(response, access, refresh):
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=30 * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


def clear_auth_cookies(response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def set_pre_auth_cookie(response, token):
    response.set_cookie(
        "pre_auth_token",
        str(token),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=300,
        path="/",
    )


def validate_password_strength(password):
    """
    Перевіряє пароль на відповідність вимогам безпеки.
    Повертає рядок з помилкою або None якщо пароль валідний.
    """
    if len(password) < 8:
        return "Мінімум 8 символів"
    if not re.search(r'[a-z]', password):
        return "Пароль повинен містити маленькі літери"
    if not re.search(r'[A-Z]', password):
        return "Пароль повинен містити великі літери"
    if not re.search(r'[0-9]', password):
        return "Пароль повинен містити цифри"
    if not re.search(r'[^a-zA-Z0-9]', password):
        return "Пароль повинен містити спецсимволи (!@#$...)"
    return None


def validate_pin(pin):
    if not pin.isdigit():
        return "PIN повинен містити лише цифри"
    if len(pin) < 4:
        return "PIN повинен містити мінімум 4 символи"
    return None


# =========================
# AUTH BACKEND
# =========================

class CookieJWTAuthentication(JWTAuthentication):

    def authenticate(self, request):
        header = self.get_header(request)

        if header:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = request.COOKIES.get("access_token")

        if raw_token is None:
            return None  # немає куки — анонімний, це нормально

        # JWT валідація (підпис, expiry)
        try:
            validated_token = self.get_validated_token(raw_token)
        except (TokenError, InvalidToken):
            raise AuthenticationFailed("Access token is invalid or expired.")

        # JTI перевірка
        jti = validated_token.get("jti")
        if not jti:
            raise AuthenticationFailed("Token is missing jti claim.")

        # DB revocation check
        try:
            db_token = ActiveToken.objects.get(jti=jti, token_type="access")
        except ActiveToken.DoesNotExist:
            raise AuthenticationFailed("Token not recognized.")

        if db_token.revoked:
            raise AuthenticationFailed("Token has been revoked.")

        user = self.get_user(validated_token)
        return (user, validated_token)


# =========================
# THROTTLES
# =========================

class LoginThrottle(AnonRateThrottle):
    scope = "login"
    rate = "5/minute"


class ChangePasswordThrottle(UserRateThrottle):
    scope = "change_password"
    rate = "1/hour"


class ChangePinThrottle(UserRateThrottle):
    scope = "change_pin"
    rate = "1/hour"


# =========================
# LOGIN (STEP 1)
# =========================

class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})

        if not serializer.is_valid():
            LoginLog.objects.create(
                email=request.data.get("email", ""),
                action=LoginLog.Action.FAILED,
            )
            return Response(serializer.errors, status=401)

        user = serializer.validated_data["user"]
        pre_auth = PreAuthToken.for_user(user)

        response = Response({
            "detail": "PIN required",
            "groups": list(user.groups.values_list("name", flat=True)),
        })
        set_pre_auth_cookie(response, pre_auth)
        return response


# =========================
# PIN VERIFY (STEP 2)
# =========================

class PinVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        raw = request.COOKIES.get("pre_auth_token")

        if not raw:
            return Response({"detail": "Session expired"}, status=401)

        try:
            token = PreAuthToken(raw)

            if token.get("token_type") != "pre_auth":
                return Response({"detail": "Invalid token"}, status=401)

            user_id = token["user_id"]

        except (TokenError, InvalidToken, KeyError):
            return Response({"detail": "Invalid session"}, status=401)

        pin = request.data.get("pin", "").strip()
        if not pin:
            return Response({"detail": "PIN required"}, status=400)

        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        ip = get_client_ip(request)
        device = get_device_info(request)

        if not user.profile.check_pin(pin):
            LoginLog.objects.create(
                user=user,
                email=user.email,
                action=LoginLog.Action.FAILED,
            )
            return Response({"detail": "Invalid PIN"}, status=401)

        # Генеруємо refresh — access_token викликаємо РІВНО ОДИН РАЗ
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token  # єдиний виклик — зберігаємо об'єкт

        now = timezone.now()

        

        ActiveToken.objects.create(
            user=user,
            jti=str(new_access["jti"]),
            token_type="access",
            expires_at=now + timedelta(minutes=30),
        )
        ActiveToken.objects.create(
            user=user,
            jti=str(new_refresh["jti"]),
            token_type="refresh",
            expires_at=now + timedelta(days=7),
        )
        LoginLog.objects.create(
            user=user,
            email=user.email,
            action=LoginLog.Action.LOGIN,
        )

      

        response = Response({"user": UserSerializer(user).data})
        response.delete_cookie("pre_auth_token")
        set_auth_cookies(response, str(access), str(refresh))
        return response


# =========================
# REFRESH
# =========================

class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get("refresh_token")
        if not raw:
            return Response({"detail": "No refresh token"}, status=401)

        try:
            old_refresh = RefreshToken(raw)
            refresh_jti = old_refresh["jti"]

            try:
                db_refresh = ActiveToken.objects.get(jti=refresh_jti, token_type="refresh")
            except ActiveToken.DoesNotExist:
                raise TokenError("Refresh token not found in DB")

            if not db_refresh.is_valid():
                raise TokenError("Refresh token is revoked or expired")

            user = db_refresh.user
            now = timezone.now()

            # Видаляємо старий access
            old_access_raw = request.COOKIES.get("access_token")
            if old_access_raw:
                try:
                    from rest_framework_simplejwt.tokens import AccessToken
                    old_access = AccessToken(old_access_raw)
                    ActiveToken.objects.filter(
                        jti=old_access["jti"], token_type="access"
                    ).delete()
                except (TokenError, InvalidToken):
                    pass

            # Ротація: видаляємо старий refresh з БД
            db_refresh.delete()
            ip = get_client_ip(request)
            device = get_device_info(request)
            # Генеруємо НОВУ пару токенів
            new_refresh = RefreshToken.for_user(user)
            new_access = new_refresh.access_token

            ActiveToken.objects.create(
                user=user,
                jti=str(new_access["jti"]),
                token_type="access",
                expires_at=now + timedelta(minutes=30),
                # ip_address=ip,
                # user_agent=device["user_agent"],
                # device_name=device["device_name"],
                # browser=device["browser"],
                # os=device["os"],
            )
            ActiveToken.objects.create(
                user=user,
                jti=str(new_refresh["jti"]),
                token_type="refresh",
                expires_at=now + timedelta(days=7),
            )

        except (TokenError, InvalidToken):
            try:
                if 'refresh_jti' in locals():
                    ActiveToken.objects.filter(jti=refresh_jti).delete()
            except Exception:
                pass

            response = Response({"detail": "Invalid refresh token"}, status=401)
            clear_auth_cookies(response)
            return response

        response = Response({"detail": "ok"})
        set_auth_cookies(response, str(new_access), str(new_refresh))
        return response


# =========================
# LOGOUT
# =========================

class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user if request.user and request.user.is_authenticated else None

        # revoke tokens (если пользователь есть)
        if user:
            ActiveToken.objects.filter(user=user).update(revoked=True)

            LoginLog.objects.create(
                user=user,
                email=user.email,
                action=LoginLog.Action.LOGOUT,
            )

        else:
            # логируем анонимный logout (опционально)
            LoginLog.objects.create(
                user=None,
                email="",
                action=LoginLog.Action.LOGOUT,

            )

        response = Response({"detail": "logged out"})
       
        return response


# =========================
# ME
# =========================

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        print('hello')
        _maybe_cleanup_expired_tokens(request.user)
        sessions = ActiveToken.objects.all(user=request.user)
        print(sessions)
        return Response(UserSerializer(request.user).data, sessions)


# =========================
# CHANGE PASSWORD
# =========================

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChangePasswordThrottle]

    def post(self, request):
        current = request.data.get("current_password", "").strip()
        new_password = request.data.get("new_password", "").strip()

        if not current or not new_password:
            return Response({"detail": "Both fields required"}, status=400)

        if not request.user.check_password(current):
            return Response({"detail": "Current password is incorrect"}, status=401)

        error = validate_password_strength(new_password)
        if error:
            return Response({"detail": error}, status=400)


        request.user.set_password(new_password)
        request.user.save()
        request.user.profile.password_changed_at = timezone.now()
        request.user.profile.save()

        # Відкликаємо всі токени — користувач має перелогінитись
        ActiveToken.objects.filter(user=request.user).update(revoked=True)

        response = Response({"detail": "Password changed. Please log in again."})
        clear_auth_cookies(response)
        return response


# =========================
# CHANGE PIN
# =========================

class ChangePinView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChangePinThrottle]

    def post(self, request):
        current_pin = request.data.get("current_pin", "").strip()
        new_pin = request.data.get("new_pin", "").strip()

        if not current_pin or not new_pin:
            return Response({"detail": "Both fields required"}, status=400)

        if not request.user.profile.check_pin(current_pin):
            return Response({"detail": "Current PIN is incorrect"}, status=401)

        error = validate_pin(new_pin)
        if error:
            return Response({"detail": error}, status=400)

        request.user.profile.set_pin(new_pin)
        request.user.profile.pin_changed_at = timezone.now()
        request.user.profile.save()

        return Response({"detail": "PIN changed successfully."})


# =========================
# CLEANUP
# =========================

def _maybe_cleanup_expired_tokens(user):
    """
    Видаляє прострочені токени одним запитом.
    """
    ActiveToken.objects.filter(
        user=user,
        expires_at__lt=timezone.now(),
    ).delete()