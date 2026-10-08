from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

# Root router connects account, inventory, POS, admin, and development media URLs.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('inventory.urls')),
    path('', include('pos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)