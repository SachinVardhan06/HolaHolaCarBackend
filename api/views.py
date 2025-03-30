from django.shortcuts import render
from rest_framework import status, generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import status, generics, filters, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from django.utils import timezone
from .models import User, Profile, Vehicle, Ride, Booking, Review
from .serializer import (
    UserSerializer, ProfileSerializer, VehicleSerializer,
    RideSerializer, BookingSerializer, ReviewSerializer
)
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework import status

# Authentication Views
# Update the RegisterView class
@api_view(['GET'])
@ensure_csrf_cookie
def get_csrf_token(request):
    return Response({
        'message': 'CSRF cookie set',
        'success': True
    })

@method_decorator(ensure_csrf_cookie, name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        try:
            print("Registration data received:", request.data)
            
            # Add phone_number to the request data if not present
            data = request.data.copy()
            if 'phone_number' not in data:
                return Response({
                    'status': 'error',
                    'message': 'Phone number is required',
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(data=data)
            if not serializer.is_valid():
                print("Validation errors:", serializer.errors)
                return Response({
                    'status': 'error',
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create the user
            user = serializer.save()
            print(f"User created successfully: {user.username}")

            # Wait for profile creation signal to complete
            user.refresh_from_db()

            # Get profile data
            profile_data = {
                'phone_number': user.phone_number,  # Get directly from user model
                'verification_status': user.profile.verification_status if hasattr(user, 'profile') else 'PENDING',
                'full_name': user.get_full_name()
            }

            return Response({
                'status': 'success',
                'message': 'Registration successful',
                'data': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone_number': user.phone_number,  # Include phone number in response
                    'profile': profile_data
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print("Registration error:", str(e))
            return Response({
                'status': 'error',
                'message': str(e) if settings.DEBUG else 'Registration failed. Please try again.',
                'error_details': str(e) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    try:
        email = request.data.get('email')
        password = request.data.get('password')

        # Debug prints
        print(f"Login attempt with email: {email}")

        # Input validation
        if not email or not password:
            return Response({
                'error': 'Please provide both email and password'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get user by email
            User = get_user_model()
            user = User.objects.get(email=email)
            print(f"Found user: {user.username}")

            # Direct password check first
            if not user.check_password(password):
                print("Password check failed")
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Check if user is active
            if not user.is_active:
                return Response({
                    'error': 'Please verify your email first'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            # Get profile data if exists
            profile_data = None
            if hasattr(user, 'profile'):
                profile_data = {
                    'phone_number': getattr(user.profile, 'phone_number', None),
                    'verification_status': getattr(user.profile, 'verification_status', None),
                    'avatar': user.profile.avatar.url if getattr(user.profile, 'avatar', None) else None,
                }

            print("Login successful")
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'profile': profile_data
                }
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            print(f"No user found with email: {email}")
            return Response({
                'error': 'No account found with this email'
            }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(f"Login error: {str(e)}")
        return Response({
            'error': 'Login failed. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Profile Views
class ProfileDetail(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return get_object_or_404(Profile, user=self.request.user)

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            return Response({
                'message': 'Profile updated successfully',
                'data': response.data
            })
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# Vehicle Views
class VehicleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Ride Views
class RideList(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RideSerializer
    
    def get_queryset(self):
        # Remove the user exclusion to see all rides including yours
        queryset = Ride.objects.filter(status='SCHEDULED')
        
        # Filter parameters
        start = self.request.query_params.get('start_location')
        end = self.request.query_params.get('end_location')
        date = self.request.query_params.get('date')
        
        if start:
            queryset = queryset.filter(start_location__icontains=start)
        if end:
            queryset = queryset.filter(end_location__icontains=end)
        if date:
            queryset = queryset.filter(date=date)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        """
        Returns rides based on filters:
        - If user param is provided, returns user's rides
        - If search params are provided, returns filtered rides
        - Otherwise returns all scheduled rides
        """
        user_id = self.request.query_params.get('user', None)
        start = self.request.query_params.get('start_location')
        end = self.request.query_params.get('end_location')
        date = self.request.query_params.get('date')
        
        # Start with all rides
        queryset = Ride.objects.all()
        
        # Filter by user if specified
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            return queryset.order_by('-created_at')
            
        # Otherwise apply search filters
        queryset = queryset.filter(status='SCHEDULED')
        if start:
            queryset = queryset.filter(start_location__icontains=start)
        if end:
            queryset = queryset.filter(end_location__icontains=end)
        if date:
            queryset = queryset.filter(date=date)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class RideDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RideSerializer
    queryset = Ride.objects.all()

    def perform_update(self, serializer):
        ride = self.get_object()
        if ride.user != self.request.user:
            raise PermissionDenied("You can only update your own rides")
        if ride.status != 'SCHEDULED':
            raise ValidationError("Cannot update a ride that's already started or completed")
        serializer.save()

# Booking Views
class BookingCreate(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        ride = serializer.validated_data['ride']
        seats_booked = serializer.validated_data['seats_booked']
        
        # Additional validations
        if ride.user == self.request.user:
            raise ValidationError("You cannot book your own ride")
        if ride.status != 'SCHEDULED':
            raise ValidationError("This ride is not available for booking")
        if ride.date < timezone.now().date():
            raise ValidationError("Cannot book past rides")
        if ride.available_seats - ride.booked_seats < seats_booked:
            raise ValidationError(f"Only {ride.available_seats - ride.booked_seats} seats available")

        # Create booking
        booking = serializer.save(
            user=self.request.user,
            status='CONFIRMED',
            total_amount=ride.price * seats_booked
        )
        
        # Update ride seats
        ride.booked_seats += seats_booked
        ride.save()
        
        return booking

class MyBookings(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['booking_date', 'status', 'total_amount']
    search_fields = ['ride__start_location', 'ride__end_location']

    def get_queryset(self):
        queryset = (
            Booking.objects
            .filter(user=self.request.user)
            .select_related('ride', 'ride__user')  # Optimize database queries
            .prefetch_related('ride__vehicle')
        )

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(booking_date__range=[start_date, end_date])

        # Filter by minimum amount
        min_amount = self.request.query_params.get('min_amount')
        if min_amount:
            queryset = queryset.filter(total_amount__gte=min_amount)

        # Filter by upcoming/past
        filter_type = self.request.query_params.get('type')
        today = timezone.now().date()
        if filter_type == 'upcoming':
            queryset = queryset.filter(ride__date__gte=today)
        elif filter_type == 'past':
            queryset = queryset.filter(ride__date__lt=today)

        return queryset.order_by('-booking_date')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)

        # Add summary statistics
        return response

# Review Views
class ReviewCreate(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        ride_id = self.kwargs.get('ride_id')
        ride = get_object_or_404(Ride, id=ride_id)
        
        # Validate booking completion
        booking = Booking.objects.filter(
            user=self.request.user,
            ride=ride,
            status='COMPLETED'
        ).first()
        
        if not booking:
            raise ValidationError("You can only review rides you've completed")
        
        # Check for existing review
        if Review.objects.filter(reviewer=self.request.user, ride=ride).exists():
            raise ValidationError("You have already reviewed this ride")
        
        serializer.save(reviewer=self.request.user, ride=ride)

# Additional API endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_ride(request, pk):
    ride = get_object_or_404(Ride, pk=pk, user=request.user)
    
    if ride.status != 'SCHEDULED':
        return Response({
            'error': 'Only scheduled rides can be cancelled'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if ride.cancel_ride():
        return Response({'message': 'Ride cancelled successfully'})
    
    return Response({
        'error': 'Failed to cancel ride'
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    reason = request.data.get('reason', '')
    
    if booking.status != 'CONFIRMED':
        return Response({
            'error': 'Only confirmed bookings can be cancelled'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if booking.cancel_booking(reason):
        return Response({'message': 'Booking cancelled successfully'})
    
    return Response({
        'error': 'Failed to cancel booking'
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_statistics(request):
    user_profile = request.user.profile
    total_rides = Ride.objects.filter(user=request.user).count()
    total_bookings = Booking.objects.filter(user=request.user).count()
    
    return Response({
        'total_rides_offered': total_rides,
        'total_rides_taken': total_bookings,
        'total_distance': user_profile.total_distance,
        'rating': user_profile.rating,
        'rides_cancelled': user_profile.rides_cancelled
    })


# ...existing code...

# Add after MyBookings class
class BookingDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        booking = self.get_object()
        if booking.status != 'CONFIRMED':
            raise ValidationError("Can only modify confirmed bookings")
        if booking.ride.date < timezone.now().date():
            raise ValidationError("Cannot modify past bookings")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != 'CONFIRMED':
            raise ValidationError("Can only cancel confirmed bookings")
        if instance.ride.date < timezone.now().date():
            raise ValidationError("Cannot cancel past bookings")
        instance.cancel_booking()

# ...existing code...

# ...existing code...

class RideReviews(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        ride_id = self.kwargs.get('ride_id')
        return Review.objects.filter(ride_id=ride_id).select_related('reviewer', 'ride')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({
                'message': 'No reviews found for this ride',
                'reviews': []
            })
        
        serializer = self.get_serializer(queryset, many=True)
        average_rating = queryset.aggregate(Avg('rating'))['rating__avg']
        
        return Response({
            'average_rating': round(float(average_rating), 1) if average_rating else 0.0,
            'total_reviews': queryset.count(),
            'reviews': serializer.data
        })

class MyReviews(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(reviewer=self.request.user).select_related('ride')


# ...existing code...

class LocationSearch(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RideSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return Ride.objects.none()

        # Search in both start and end locations
        return Ride.objects.filter(
            Q(start_location__icontains=query) | 
            Q(end_location__icontains=query)
        ).distinct().values_list(
            'start_location', 'end_location'
        ).distinct()[:10]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        locations = set()
        
        for start_loc, end_loc in queryset:
            if start_loc and start_loc.lower().__contains__(request.query_params.get('q', '').lower()):
                locations.add(start_loc)
            if end_loc and end_loc.lower().__contains__(request.query_params.get('q', '').lower()):
                locations.add(end_loc)

        return Response({
            'locations': sorted(list(locations))
        })
    
# Add these imports if not already present
from django.contrib.auth import get_user_model
from rest_framework import filters

# Add this class after LocationSearch
class UserSearch(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return User.objects.none()

        return User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        ).exclude(id=self.request.user.id)[:10]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'users': [{
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            } for user in serializer.data]
        })
    
# Add these imports at the top if not present
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    try:
        # Decode the token
        uid = force_str(urlsafe_base64_decode(token))
        user = User.objects.get(pk=uid)
        
        if not user.is_active:
            # Activate user
            user.is_active = True
            user.save()
            
            # Update profile verification status
            if hasattr(user, 'profile'):
                user.profile.verification_status = 'VERIFIED'
                user.profile.save()
            
            return Response({
                'message': 'Email verified successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'Email already verified'
            }, status=status.HTTP_200_OK)
            
    except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
        return Response({
            'error': 'Invalid verification token'
        }, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        # Get refresh token from request data
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Blacklist the refresh token
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            # Token is invalid or already blacklisted
            pass

        return Response({'detail': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

@api_view(['GET'])
@permission_classes([AllowAny])  # Allow any user to access this endpoint
def search_rides(request):
    try:
        start_location = request.query_params.get('start_location', '')
        end_location = request.query_params.get('end_location', '')
        date = request.query_params.get('date', '')

        if not all([start_location, end_location, date]):
            return Response(
                {'detail': 'Missing required parameters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Query scheduled rides
        rides = Ride.objects.filter(
            status='SCHEDULED',
            date=date,
            start_location__icontains=start_location,
            end_location__icontains=end_location
        )

        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class VehicleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def user_vehicles(self, request):
        vehicles = self.get_queryset()
        serializer = self.get_serializer(vehicles, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

