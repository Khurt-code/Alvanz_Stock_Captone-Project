from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


# Shared role guards. manager_required protects Sales & Reports; inventory_manager_required blocks
# cashier/staff from inventory write actions (add/edit/delete products, categories, stock movements).
def manager_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_manager:
            messages.error(request, "You don't have permission to view Sales & Reports.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped


def inventory_manager_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_manager:
            messages.error(request, "You don't have permission to manage inventory.")
            return redirect("pos_screen")
        return view_func(request, *args, **kwargs)

    return _wrapped
