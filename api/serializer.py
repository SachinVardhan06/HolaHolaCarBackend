from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Profile, Vehicle, Ride, Booking, Review
import re

class UserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2', 'phone_number')
        extra_kwargs = {
            'password': {'write_only': True},
            'phone_number': {'required': True}
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Validate phone number format
        if not re.match(r'^\d{10}$', data['phone_number']):
            raise serializers.ValidationError({
                'phone_number': 'Phone number must be exactly 10 digits'
            })
        
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        
        return user

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ('id', 'user', 'vehicle_type', 'make', 'model', 'year', 
                 'color', 'vehicle_number', 'insurance_valid_till', 
                 'air_conditioned', 'verified', 'documents')
        read_only_fields = ('verified',)

    def validate_insurance_valid_till(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Insurance has expired")
        return value

class ProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)  # Add this line
    vehicles = VehicleSerializer(source='user.vehicles', many=True, read_only=True)
    total_earnings = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('id', 'user', 'username', 'user_email', 'full_name', 'bio', 
                 'image', 'verified', 'verification_status', 'gender', 
                 'date_of_birth', 'address', 'city', 'state', 'driving_license', 
                 'driving_license_verified', 'rating', 'total_rides', 'user_phone',
                 'total_distance', 'rides_cancelled', 'vehicles', 'total_earnings',
                 'created_at', 'updated_at')
        read_only_fields = ('verified', 'verification_status', 
                           'driving_license_verified', 'rating', 'total_rides', 
                           'total_distance', 'rides_cancelled')

    def get_total_earnings(self, obj):
        from django.db.models import Sum
        earnings = Booking.objects.filter(
            ride__user=obj.user, 
            status='COMPLETED'
        ).aggregate(
            total=Sum('total_amount')
        )['total']
        return earnings or 0

class RideSerializer(serializers.ModelSerializer):
    driver_details = ProfileSerializer(source='user.profile', read_only=True)
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    available_seats_display = serializers.SerializerMethodField()
    bookings_count = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = ('id', 'user', 'driver_details', 'vehicle', 'vehicle_details',
                 'start_location', 'end_location', 'start_latitude', 
                 'start_longitude', 'end_latitude', 'end_longitude', 'price', 
                 'start_time', 'end_time', 'date', 'distance', 'available_seats',
                 'booked_seats', 'available_seats_display', 'status', 'note',
                 'allow_pets', 'smoking_allowed', 'bookings_count', 
                 'reviews_count', 'average_rating', 'created_at', 'updated_at')
        read_only_fields = ('booked_seats', 'status')

    def get_available_seats_display(self, obj):
        remaining = obj.available_seats - obj.booked_seats
        return f"{remaining} {'seat' if remaining == 1 else 'seats'} available"

    def get_bookings_count(self, obj):
        return obj.bookings.count()

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        from django.db.models import Avg
        avg = obj.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else None

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time"})
        if data['available_seats'] < 1:
            raise serializers.ValidationError(
                {"available_seats": "Available seats must be at least 1"})
        if 'vehicle' in data and not data['vehicle'].verified:
            raise serializers.ValidationError(
                {"vehicle": "Selected vehicle is not verified"})
        return data

# class BookingSerializer(serializers.ModelSerializer):
#     ride_details = RideSerializer(source='ride', read_only=True)
#     user_details = ProfileSerializer(source='user.profile', read_only=True)
#     has_reviewed = serializers.SerializerMethodField()

#     class Meta:
#         model = Booking
#         fields = ('id', 'ride', 'ride_details', 'user', 'user_details',
#                  'seats_booked', 'booking_date', 'status', 'payment_status',
#                  'total_amount', 'cancellation_reason', 'pickup_location',
#                  'drop_location', 'has_reviewed')
#         read_only_fields = ('booking_date', 'status', 'total_amount')

#     def get_has_reviewed(self, obj):
#         return obj.ride.reviews.filter(reviewer=obj.user).exists()

#     def validate(self, data):
#         ride = data['ride']
#         seats_requested = data['seats_booked']
#         available_seats = ride.available_seats - ride.booked_seats

#         if seats_requested > available_seats:
#             raise serializers.ValidationError(
#                 f"Only {available_seats} seats available for this ride")
#         if seats_requested < 1:
#             raise serializers.ValidationError("Must book at least one seat")
        
#         # Calculate total amount
#         data['total_amount'] = ride.price * seats_requested
#         return data

import datetime
from django.utils import timezone

class BookingSerializer(serializers.ModelSerializer):
    ride_details = RideSerializer(source='ride', read_only=True)
    user_details = ProfileSerializer(source='user.profile', read_only=True)
    has_reviewed = serializers.SerializerMethodField()
    driver_name = serializers.CharField(source='ride.user.get_full_name', read_only=True)
    vehicle_info = serializers.SerializerMethodField()
    booking_status_display = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'ride', 'ride_details', 'user', 'user_details',
            'seats_booked', 'booking_date', 'status', 'total_amount',
            'has_reviewed', 'driver_name', 'vehicle_info',
            'booking_status_display', 'can_cancel'
        )
        read_only_fields = ('booking_date', 'status', 'total_amount')

    def get_has_reviewed(self, obj):
        return Review.objects.filter(
            reviewer=obj.user,
            ride=obj.ride
        ).exists()

    def get_vehicle_info(self, obj):
        if obj.ride and obj.ride.vehicle:
            vehicle = obj.ride.vehicle
            return {
                'make': vehicle.make,
                'model': vehicle.model,
                'color': vehicle.color,
                'vehicle_number': vehicle.vehicle_number,
                'air_conditioned': vehicle.air_conditioned
            }
        return None

    def get_booking_status_display(self, obj):
        status_map = {
            'CONFIRMED': 'Booking Confirmed',
            'CANCELLED': 'Booking Cancelled',
            'COMPLETED': 'Ride Completed',
            'PENDING': 'Pending Confirmation'
        }
        return status_map.get(obj.status, obj.status)

    def get_can_cancel(self, obj):
        if obj.status != 'CONFIRMED':
            return False
        return obj.ride.date >= timezone.now().date()

    def validate(self, data):
        ride = data.get('ride')
        seats_requested = data.get('seats_booked')

        if not ride or not seats_requested:
            raise serializers.ValidationError("Ride and seats_booked are required")

        # Check seat availability
        if ride.available_seats < seats_requested:
            raise serializers.ValidationError(
                f"Only {ride.available_seats} seats available"
            )

        # Check if user is booking their own ride
        if ride.user == self.context['request'].user:
            raise serializers.ValidationError("You cannot book your own ride")

        # Check if ride date is in the past
        if ride.date < timezone.now().date():
            raise serializers.ValidationError("Cannot book past rides")

        return data

    def create(self, validated_data):
        validated_data['total_amount'] = (
            validated_data['ride'].price * validated_data['seats_booked']
        )
        validated_data['status'] = 'CONFIRMED'
        return super().create(validated_data)
    

class ReviewSerializer(serializers.ModelSerializer):
    reviewer_details = ProfileSerializer(source='reviewer.profile', read_only=True)
    ride_details = RideSerializer(source='ride', read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'ride', 'ride_details', 'reviewer', 'reviewer_details',
                 'rating', 'comment', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, data):
        # Check if user has booked this ride
        if not Booking.objects.filter(
            user=data['reviewer'],
            ride=data['ride'],
            status='COMPLETED'
        ).exists():
            raise serializers.ValidationError(
                "You can only review rides you have completed")
        
        # Check if user has already reviewed this ride
        if Review.objects.filter(
            reviewer=data['reviewer'],
            ride=data['ride']
        ).exists():
            raise serializers.ValidationError(
                "You have already reviewed this ride")
        
        return data

    def validate_rating(self, value):
        if not 1.0 <= value <= 5.0:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value