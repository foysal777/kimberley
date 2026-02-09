import random
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

def generate_otp() -> str:
    return f"{random.randint(0, 9999):04d}"

def otp_expiry_time():
    minutes = getattr(settings, "OTP_EXP_MINUTES", 10)
    return timezone.now() + timedelta(minutes=minutes)

def send_otp_email(email: str, code: str, purpose: str):
    subject = "Your Aurelle OTP Code"
    msg = f"Your OTP for {purpose} is: {code}. It will expire soon."
    send_mail(subject, msg, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
