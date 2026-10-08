from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render


# Supplies the login template used by accounts/urls.py; other auth routes use Django defaults.
class AlvanzLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

@login_required
def real_time_stock(request):
    # Unused legacy view; the active stock route is inventory.views.real_time_stock.
    return render(request, "inventory/real_time_stock.html")