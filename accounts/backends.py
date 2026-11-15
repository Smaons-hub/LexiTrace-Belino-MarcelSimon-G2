from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.views.decorators.debug import sensitive_variables

UserModel = get_user_model()


class UsernameOrEmailBackend(ModelBackend):
    @staticmethod
    def find_user(login):
        login = (login or '').strip()
        if not login:
            return None
        matches = list(
            UserModel._default_manager.filter(Q(username__iexact=login) | Q(email__iexact=login))
        )
        if not matches:
            return None
        matches.sort(key=lambda user: (
            user.username != login,
            user.username.lower() != login.lower(),
            user.pk,
        ))
        return matches[0]

    @sensitive_variables('password')
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None
        user = self.find_user(username)
        if user is None:
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    @sensitive_variables('password')
    async def aauthenticate(self, request, username=None, password=None, **kwargs):
        return await sync_to_async(self.authenticate)(request, username, password, **kwargs)
