

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Avg, Count
from .models import User, Profile, Vehicle, Ride, Booking, Review

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'phone_number', 'get_verification_status', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('Account Information', {
            'fields': ('email', 'username', 'phone_number', 'password')
        }),
        ('Personal Details', {
            'fields': ('first_name', 'last_name')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'phone_number', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')
    
    def get_verification_status(self, obj):
        try:
            if obj.profile.verified:
                return format_html('<span style="color: green;">✓ Verified</span>')
            return format_html('<span style="color: orange;">⋯ Pending</span>')
        except Profile.DoesNotExist:
            return format_html('<span style="color: red;">✗ No Profile</span>')
    get_verification_status.short_description = 'Verification'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('get_user_info', 'get_phone', 'verification_status','get_verification_status', 'get_license_status', 'get_rating_display')
    list_filter = ('verified', 'gender', 'driving_license_verified')
    search_fields = ('full_name', 'user__email', 'user__phone_number', 'driving_license')
    readonly_fields = ('rating', 'total_rides', 'total_distance', 'rides_cancelled')
    actions = ['mark_as_verified', 'mark_as_pending', 'mark_as_rejected']
    list_editable = ('verification_status',)
    
    fieldsets = (
        ('User Information', {
            'fields': (
                'user', 'full_name', 'gender', 'date_of_birth', 'image'
            )
        }),
        ('Verification', {
            'fields': (
                'verification_status',  # Add this field
                'verified',
                'driving_license',
                'driving_license_verified'
            )
        }),
        ('Contact Information', {
            'fields': (
                'address', 'city', 'state'
            )
        }),
        ('Statistics', {
            'fields': (
                'rating', 'total_rides', 'total_distance', 'rides_cancelled'
            )
        }),
    )
    def get_verification_status(self, obj):
        status_colors = {
            'VERIFIED': 'green',
            'PENDING': 'orange',
            'REJECTED': 'red'
        }
        return format_html(
            '<span style="color: {};">● {}</span>',
            status_colors.get(obj.verification_status, 'gray'),
            obj.verification_status
        )
    get_verification_status.short_description = 'Status'

    def mark_as_verified(self, request, queryset):
        updated = queryset.update(
            verification_status='VERIFIED',
            verified=True
        )
        self.message_user(request, f'{updated} profiles marked as verified.')
    mark_as_verified.short_description = "Mark selected profiles as VERIFIED"

    def mark_as_pending(self, request, queryset):
        updated = queryset.update(
            verification_status='PENDING',
            verified=False
        )
        self.message_user(request, f'{updated} profiles marked as pending.')
    mark_as_pending.short_description = "Mark selected profiles as PENDING"

    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(
            verification_status='REJECTED',
            verified=False
        )
        self.message_user(request, f'{updated} profiles marked as rejected.')
    mark_as_rejected.short_description = "Mark selected profiles as REJECTED"
    
    def get_user_info(self, obj):
        return format_html(
            '<div><strong>{}</strong><br/><small>{}</small></div>',
            obj.full_name or obj.user.username,
            obj.user.email
        )
    get_user_info.short_description = 'User Details'
    
    def get_phone(self, obj):
        return format_html('<code>{}</code>', obj.user.phone_number)
    get_phone.short_description = 'Phone'
    
    def get_license_status(self, obj):
        if obj.driving_license_verified:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                obj.driving_license
            )
        return format_html(
            '<span style="color: orange;">⋯ {}</span>',
            obj.driving_license or 'Not Provided'
        )
    get_license_status.short_description = 'License'
    
    def get_rating_display(self, obj):
        rating = obj.rating or 0
        stars = '★' * int(rating) + '☆' * (5 - int(rating))
        return format_html(
            '<span style="color: gold;">{}</span> {}',
            stars,
            str(round(rating, 1))
        )
    get_rating_display.short_description = 'Rating'
    
    actions = ['verify_users', 'verify_licenses', 'reject_verification']
    
    def verify_users(self, request, queryset):
        updated = queryset.update(verified=True)
        self.message_user(request, f'{updated} users were successfully verified.')
    verify_users.short_description = "Mark selected users as verified"
    
    def verify_licenses(self, request, queryset):
        updated = queryset.update(driving_license_verified=True)
        self.message_user(request, f'{updated} licenses were successfully verified.')
    verify_licenses.short_description = "Verify driving licenses"
    
    def reject_verification(self, request, queryset):
        updated = queryset.update(verified=False)
        self.message_user(request, f'{updated} verifications were rejected.')
    reject_verification.short_description = "Reject verification"

    

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('get_vehicle_info', 'get_owner', 'vehicle_type', 'verified', 'get_verified_status', 'get_insurance_status')
    list_filter = ('vehicle_type', 'verified', 'air_conditioned')
    search_fields = ('registration_number', 'user__username', 'make', 'model')
    list_editable = ('verified',)
    actions = ['verify_vehicles', 'unverify_vehicles']

    def get_vehicle_info(self, obj):
        return format_html('{} {} {}', obj.year, obj.make, obj.model)
    get_vehicle_info.short_description = 'Vehicle'

    def get_owner(self, obj):
        return obj.user.username
    get_owner.short_description = 'Owner'
    
    def get_verified_status(self, obj):
        return format_html(
            '<span style="color: {};">● {}</span>',
            'green' if obj.verified else 'orange',
            'Verified' if obj.verified else 'Pending'
        )
    get_verified_status.short_description = 'Status'
    
    def get_insurance_status(self, obj):
        if not hasattr(obj, 'insurance_valid_till'):
            return format_html('<span style="color: gray;">Not Available</span>')
            
        if obj.insurance_valid_till > timezone.now().date():
            days_left = (obj.insurance_valid_till - timezone.now().date()).days
            return format_html(
                '<span style="color: green;">{} days left</span>', 
                days_left
            )
        return format_html('<span style="color: red;">Expired</span>')
    get_insurance_status.short_description = 'Insurance'
    
    def verify_vehicles(self, request, queryset):
        updated = queryset.update(verified=True)
        self.message_user(request, f'{updated} vehicles have been verified.')
    verify_vehicles.short_description = "Mark selected vehicles as verified"
    
    def unverify_vehicles(self, request, queryset):
        updated = queryset.update(verified=False)
        self.message_user(request, f'{updated} vehicles have been unverified.')
    unverify_vehicles.short_description = "Mark selected vehicles as unverified"



@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_driver', 'get_route', 'date', 'get_price', 'status')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'start_location', 'end_location')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_completed', 'mark_as_cancelled']

    def get_driver(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:api_user_change', args=[obj.user.id]),
            obj.user.username
        )
    get_driver.short_description = 'Driver'

    def get_route(self, obj):
        return format_html('{} → {}', obj.start_location, obj.end_location)
    get_route.short_description = 'Route'


    def get_price(self, obj):
        return format_html('₹{}', obj.price)
    get_price.short_description = 'Price'

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f'{updated} rides marked as completed.')
    mark_as_completed.short_description = "Mark selected rides as completed"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'{updated} rides marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected rides as cancelled"

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user', 'get_ride', 'get_seats', 'get_status', 'get_created_at')
    list_filter = ('status', 'booking_date')  # Changed from created_at to booking_date
    search_fields = ('user__username', 'ride__start_location', 'ride__end_location')
    readonly_fields = ('booking_date',)  # Changed from created_at to booking_date
    
    def get_user(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:api_user_change', args=[obj.user.id]),
            obj.user.username
        )
    get_user.short_description = 'User'

    def get_ride(self, obj):
        return format_html(
            '{} → {} ({})',
            obj.ride.start_location,
            obj.ride.end_location,
            obj.ride.date.strftime('%d %b %Y')
        )
    get_ride.short_description = 'Ride Details'

    def get_seats(self, obj):
        return obj.seats_booked
    
    get_seats.short_description = 'Seats'

    def get_status(self, obj):
        status_colors = {
            'CONFIRMED': 'green',
            'PENDING': 'orange',
            'CANCELLED': 'red'
        }
        return format_html(
            '<span style="color: {};">● {}</span>',
            status_colors.get(obj.status, 'gray'),
            obj.status
        )
    get_status.short_description = 'Status'

    def get_created_at(self, obj):
        return obj.booking_date.strftime('%d %b %Y %H:%M')
    get_created_at.short_description = 'Booked On'
    
    actions = ['confirm_bookings', 'cancel_bookings']
    
    def confirm_bookings(self, request, queryset):
        updated = queryset.update(status='CONFIRMED')
        self.message_user(request, f'{updated} bookings have been confirmed.')
    confirm_bookings.short_description = "Confirm selected bookings"
    
    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'{updated} bookings have been cancelled.')
    cancel_bookings.short_description = "Cancel selected bookings"