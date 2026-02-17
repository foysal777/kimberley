from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone




class User(AbstractUser):
    PLAN_FREE = "FREE"
    PLAN_PREMIUM = "PREMIUM"

    PLAN_CHOICES = (
        (PLAN_FREE, "Free"),
        (PLAN_PREMIUM, "Premium"),
    )
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)  # keep for Django admin compatibility
    is_email_verified = models.BooleanField(default=False)
    plan_type = models.CharField(max_length=20,choices=PLAN_CHOICES,default=PLAN_FREE)
    plan_expire_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"] 




    def is_premium(self):
      
        if self.plan_type != self.PLAN_PREMIUM:
            return False
        if self.plan_expire_at and self.plan_expire_at < timezone.now():
            return False
        return True

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
    full_name = models.CharField(max_length=150 , blank=True, default="")
    role = models.CharField(max_length=120, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=180, blank=True)
    what_hoping_to_gain = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    # Example: ["Mon","Tue"] or ["All"]
    available_days = models.JSONField(default=list, blank=True)
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    # Connect taxonomy selections to profile
    selected_items = models.ManyToManyField(TaxonomyItem, through="UserProfileSelection", blank=True)
    is_online = models.BooleanField(default=False)  # for future use: online status
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user_id}: {self.full_name} user.email={self.user.email})"



class ProfileView(models.Model):
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="views_made")
    viewed_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="views_received")
    created_at = models.DateTimeField(auto_now_add=True)






class UserLocation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="location")
    latitude = models.FloatField()
    longitude = models.FloatField()




class Available(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability")
    is_available = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)  # if False, hide from swipe deck and connections list


class UserProfileSelection(models.Model):
    """
    Join table: profile <-> taxonomy item
    """
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    item = models.ForeignKey(TaxonomyItem, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "item")










from django.db import models


class LegalDocument(models.Model):
    TYPE_PRIVACY = "PRIVACY"
    TYPE_TERMS = "TERMS"

    TYPE_CHOICES = (
        (TYPE_PRIVACY, "Privacy Policy"),
        (TYPE_TERMS, "Terms & Conditions"),
    )

    doc_type = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()  
    version = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.doc_type} v{self.version}"
