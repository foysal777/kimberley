from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    """
    Single user model. We’ll use email as the primary login field.
    """
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)  # keep for Django admin compatibility
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  # required when creating superuser

    def __str__(self):
        return self.email


class EmailOTP(models.Model):
    PURPOSE_CHOICES = (
        ("REGISTER", "REGISTER"),
        ("RESET", "RESET"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    send_count = models.PositiveIntegerField(default=0)

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.user.email} - {self.purpose} - {self.code}"





# ------------ Profile model --------------------
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

class TaxonomyCategory(models.Model):

    """
    Heading (Accordion title)
    Example: "Connection & Relationship-led"
    """
    TYPE_CHOICES = (
        ("INTENTION", "INTENTION"),
        ("SKILL", "SKILL"),
        ("OTHER", "OTHER"),
    )

    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="INTENTION")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.type}: {self.title}"


class TaxonomyItem(models.Model):
    """
    Bullet point (checkbox item)
    Example: "To form deeper, more meaningful connections"
    """
    category = models.ForeignKey(TaxonomyCategory, on_delete=models.CASCADE, related_name="items")
    text = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=120, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=180, blank=True)
    what_hoping_to_gain = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    # Example: ["Mon","Tue"] or ["All"]
    available_days = models.JSONField(default=list, blank=True)
    time_range = models.CharField(max_length=60, blank=True)  
    # Connect taxonomy selections to profile
    selected_items = models.ManyToManyField(TaxonomyItem, through="UserProfileSelection", blank=True)
    is_online = models.BooleanField(default=False)  # for future use: online status
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user_id}: {self.full_name} user.email={self.user.email})"


class UserLocation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="location")
    latitude = models.FloatField()
    longitude = models.FloatField()


class UserProfileSelection(models.Model):
    """
    Join table: profile <-> taxonomy item
    """
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    item = models.ForeignKey(TaxonomyItem, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "item")
