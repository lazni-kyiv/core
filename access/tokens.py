from datetime import timedelta
from rest_framework_simplejwt.tokens import Token

class PreAuthToken(Token):
    token_type = 'pre_auth'
    lifetime = timedelta(minutes=5)

    @classmethod
    def for_user(cls, user):
        token = cls()
        token['user_id'] = user.id
        return token