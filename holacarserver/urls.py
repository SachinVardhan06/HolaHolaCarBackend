# from django.contrib import admin
# from django.urls import path, include
# from django.contrib.auth import views as auth_views

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/', include('api.urls')),
#     # ...other url patterns...
# ]

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Include your API urls
    # Add a root path view
    path('', include('api.urls')),  # This will handle the root URL
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Add this if you want to handle 404 errors gracefully
handler404 = 'api.views.custom_404'
