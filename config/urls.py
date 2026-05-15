from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('stock/', include('stock.urls')),
    path('sales/', include('sales.urls')),
    path('clients/', include('clients.urls')),
    path('sav/', include('sav.urls')),
    path('audit/', include('audit.urls')),
]

handler404 = 'dashboard.views.error_404'
handler500 = 'dashboard.views.error_500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
