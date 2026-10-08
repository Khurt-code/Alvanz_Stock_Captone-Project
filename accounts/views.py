from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render


class AlvanzLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

@login_required
def real_time_stock(request):
    return render(request, "inventory/real_time_stock.html")