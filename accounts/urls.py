from django.urls import path

from .views import AlvanzLoginView

# Account-specific routes; project URLs also include Django's built-in auth endpoints.
urlpatterns = [
    path("login/", AlvanzLoginView.as_view(), name="login"),
]