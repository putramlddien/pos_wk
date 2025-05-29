from django.http import HttpResponseForbidden
from django.contrib.auth.views import redirect_to_login

def role_required(allowed_roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages = request._messages if hasattr(request, '_messages') else None
                if messages:
                    messages.error(request, "Silakan login terlebih dahulu.")
                return redirect_to_login(request.get_full_path(), 'kasir_owner_login')
            if request.user.role not in allowed_roles:
                return HttpResponseForbidden("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
