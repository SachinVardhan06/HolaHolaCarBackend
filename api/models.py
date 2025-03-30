from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

class User(AbstractUser):
    username = models.CharField(max_length=300)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=10, validators=[
        RegexValidator(
            regex=r'^\d{10}$',
            message='Phone number must be 10 digits'
        )
    ])
    unique=True
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    def get_full_name(self):
        return self.profile.full_name if hasattr(self, 'profile') else self.username

class Profile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ]
    
    VERIFICATION_STATUS = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=300)
    bio = models.TextField(max_length=500, blank=True)
    image = models.ImageField(default='default.jpg', upload_to="user_images")
    verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=10, 
        choices=VERIFICATION_STATUS, 
        default='PENDING'
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    driving_license = models.CharField(max_length=50, blank=True)
    driving_license_verified = models.BooleanField(default=False)
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    total_rides = models.PositiveIntegerField(default=0)
    total_distance = models.PositiveIntegerField(default=0)  # in kilometers
    rides_cancelled = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'

    def __str__(self):
        return self.full_name

    def update_rating(self):
        reviews = Review.objects.filter(ride__user=self.user)
        if reviews.exists():
            self.rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.save()

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('SEDAN', 'Sedan'),
        ('SUV', 'SUV'),
        ('HATCHBACK', 'Hatchback'),
        ('OTHER', 'Other')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    color = models.CharField(max_length=50)
    vehicle_number = models.CharField(max_length=20, unique=True)
    insurance_valid_till = models.DateField()
    air_conditioned = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    documents = models.FileField(upload_to='vehicle_documents/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.vehicle_number})"

class Ride(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rides_offered')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, related_name='rides')
    start_location = models.CharField(max_length=200)
    end_location = models.CharField(max_length=200)
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    end_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    end_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    date = models.DateField()
    distance = models.PositiveIntegerField(help_text="Distance in kilometers", default=0)
    available_seats = models.PositiveIntegerField(default=4)
    booked_seats = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    note = models.TextField(max_length=500, blank=True)
    allow_pets = models.BooleanField(default=False)
    smoking_allowed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ride'
        verbose_name_plural = 'Rides'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ride by {self.user.username} from {self.start_location} to {self.end_location}"

    def cancel_ride(self):
        if self.status == 'SCHEDULED':
            self.status = 'CANCELLED'
            self.user.profile.rides_cancelled += 1
            self.user.profile.save()
            self.save()
            return True
        return False

    def complete_ride(self):
        if self.status == 'ONGOING':
            self.status = 'COMPLETED'
            self.user.profile.total_rides += 1
            self.user.profile.total_distance += self.distance
            self.user.profile.save()
            self.save()
            return True
        return False


# ... existing code ...

class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed')
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('REFUNDED', 'Refunded'),
        ('FAILED', 'Failed')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='bookings')
    seats_booked = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    cancellation_reason = models.TextField(blank=True)
    pickup_location = models.CharField(max_length=200, blank=True)
    drop_location = models.CharField(max_length=200, blank=True)
    
    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-booking_date']

    def __str__(self):
        return f"Booking {self.id} by {self.user.username} for {self.ride}"

    def cancel_booking(self, reason=''):
        if self.status == 'CONFIRMED':
            self.status = 'CANCELLED'
            self.cancellation_reason = reason
            self.ride.booked_seats -= self.seats_booked
            self.ride.save()
            self.save()
            return True
        return False

class Review(models.Model):
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='reviews')
    rating = models.FloatField(
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    comment = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        unique_together = ['reviewer', 'ride']

    def __str__(self):
        return f"Review by {self.reviewer.username} for ride {self.ride.id}"

# Signal handlers
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance when a new User is created"""
    if created:
        Profile.objects.create(user=instance)

def update_ride_on_booking(sender, instance, created, **kwargs):
    """Update ride statistics when a booking is created"""
    if created and instance.status == 'CONFIRMED':
        ride = instance.ride
        ride.booked_seats += instance.seats_booked
        ride.save()

def update_profile_on_review(sender, instance, created, **kwargs):
    """Update user profile rating when a review is created/updated"""
    if instance.ride.user.profile:
        instance.ride.user.profile.update_rating()

# Connect signals
post_save.connect(create_user_profile, sender=User)
post_save.connect(update_ride_on_booking, sender=Booking)
post_save.connect(update_profile_on_review, sender=Review)