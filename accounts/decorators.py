from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import User


def role_required(role):
    if role not in User.Role.values:
        raise ValueError(f'Unknown role: {role!r}')

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role != role:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
