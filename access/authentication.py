# access/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from .models import ActiveToken

class CookieJWTAuthentication(JWTAuthentication):

    def authenticate(self, request):
        access_token = request.COOKIES.get('access_token')

        if not access_token:
            return None  # нет куки → просто anonymous

        try:
            validated = self.get_validated_token(access_token)
        except (InvalidToken, TokenError):
            return None  # ❗ ВАЖНО: не raise

        jti = validated.get('jti')

        try:
            token_record = ActiveToken.objects.get(jti=jti)
            if not token_record.is_valid():
                return None
        except ActiveToken.DoesNotExist:
            return None

        return self.get_user(validated), validated