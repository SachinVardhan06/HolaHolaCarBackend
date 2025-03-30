from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication URLs
    path('csrf/', views.get_csrf_token, name='csrf_token'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile URLs
    path('profile/', views.ProfileDetail.as_view(), name='profile-detail'),
    path('profile/stats/', views.user_statistics, name='user-statistics'),
    
    # Vehicle URLs
    path('vehicles/', views.VehicleViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='vehicle-list'),
    path('vehicles/<int:pk>/', views.VehicleViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='vehicle-detail'),
     path('vehicles/user/', views.VehicleViewSet.as_view({
        'get': 'user_vehicles'
    }), name='user-vehicles'),
    
    # Ride URLs
    path('rides/', views.RideList.as_view(), name='ride-list'),
    path('rides/search/', views.search_rides, name='search-rides'),
    path('rides/<int:pk>/', views.RideDetail.as_view(), name='ride-detail'),
    path('rides/<int:pk>/cancel/', views.cancel_ride, name='cancel-ride'),
    path('rides/my-rides/', views.RideList.as_view(), name='my-rides'),
    
    # Booking URLs
    path('bookings/create/', views.BookingCreate.as_view(), name='booking-create'),
    path('bookings/my/', views.MyBookings.as_view(), name='my-bookings'),
    path('bookings/<int:pk>/', views.BookingDetail.as_view(), name='booking-detail'),
    path('bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel-booking'),
    
    # Review URLs
    path('rides/<int:ride_id>/reviews/', views.RideReviews.as_view(), name='ride-reviews'),
    path('rides/<int:ride_id>/reviews/create/', views.ReviewCreate.as_view(), name='create-review'),
    path('reviews/my/', views.MyReviews.as_view(), name='my-reviews'),
    
    # Search and Filter URLs
    path('search/locations/', views.LocationSearch.as_view(), name='location-search'),
    path('search/users/', views.UserSearch.as_view(), name='user-search'),
    
    # Additional Utility URLs
    path('verify-email/<str:token>/', views.verify_email, name='verify-email'),
    # path('reset-password/', views.ResetPassword.as_view(), name='reset-password'),
    # path('reset-password/confirm/<str:token>/', views.ResetPasswordConfirm.as_view(), 
    #      name='reset-password-confirm'),
]