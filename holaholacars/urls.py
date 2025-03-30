from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

# Define a simple view for the root URL
def home_view(request):
    return HttpResponse("Welcome to HolaHolaCars!")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Include API URLs
    path('', home_view, name='home'),  # Add this line for the root URL
]