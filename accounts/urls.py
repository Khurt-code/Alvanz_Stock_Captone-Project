from django.urls import path

from .views import AlvanzLoginView

urlpatterns = [
    path("login/", AlvanzLoginView.as_view(), name="login"),
]