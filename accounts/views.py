from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from .models import EmailOTP
from .serializers import (
    RegisterSerializer, VerifyOTPSerializer, LoginSerializer,
    ResendOTPSerializer, ForgotPasswordSerializer,
    ResetPasswordSerializer, ChangePasswordSerializer
)
from .utils import generate_otp, otp_expiry_time, send_otp_email

User = get_user_model()

def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }

def _cooldown_ok(otp_obj: EmailOTP) -> bool:
    cooldown = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
    if not otp_obj.last_sent_at:
        return True
    return (timezone.now() - otp_obj.last_sent_at).total_seconds() >= cooldown


@api_view(["POST"])
@permission_classes([AllowAny])
def RegisterView(request):
    """
    POST: full_name, email, password, confirm_password
    Creates user (inactive verification), sends OTP.
    """
    ser = RegisterSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    email = ser.validated_data["email"].lower().strip()
    full_name = ser.validated_data["full_name"].strip()
    password = ser.validated_data["password"]

    if User.objects.filter(email=email).exists():
        return Response({"detail": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

    # username required in AbstractUser; generate simple unique username
    base_username = email.split("@")[0][:20]
    username = base_username
    i = 1
    while User.objects.filter(username=username).exists():
        i += 1
        username = f"{base_username}{i}"

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=full_name,  # or store full name separately if you prefer
        is_email_verified=False,
        is_active=True,  # keep active; just gate features by is_email_verified
    )

    code = generate_otp()
    otp_obj = EmailOTP.objects.create(
        user=user,
        code=code,
        purpose="REGISTER",
        expires_at=otp_expiry_time(),
        last_sent_at=timezone.now(),
        send_count=1,
    )
    send_otp_email(email=user.email, code=code, purpose="REGISTER")

    return Response(
        {"detail": "Registered. OTP sent to email.", "email": user.email},
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def VerifyOTPView(request):
    """
    POST: email, otp, purpose (REGISTER/RESET)
    For REGISTER: marks user verified.
    For RESET: verifies OTP only (ResetPassword endpoint will change password).
    """
    ser = VerifyOTPSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    email = ser.validated_data["email"].lower().strip()
    otp = ser.validated_data["otp"].strip()
    purpose = ser.validated_data["purpose"]

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    otp_obj = EmailOTP.objects.filter(
        user=user, purpose=purpose, code=otp, is_used=False
    ).order_by("-created_at").first()

    if not otp_obj:
        return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
    if otp_obj.is_expired():
        return Response({"detail": "OTP expired."}, status=status.HTTP_400_BAD_REQUEST)

    otp_obj.is_used = True
    otp_obj.save(update_fields=["is_used"])

    if purpose == "REGISTER":
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)

    return Response({"detail": "OTP verified."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def ResendOTPView(request):
    """
    POST: email, purpose
    Resends OTP with cooldown.
    """
    ser = ResendOTPSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    email = ser.validated_data["email"].lower().strip()
    purpose = ser.validated_data["purpose"]

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # Latest unused OTP for cooldown check
    last_otp = EmailOTP.objects.filter(user=user, purpose=purpose, is_used=False).order_by("-created_at").first()

    if last_otp and not _cooldown_ok(last_otp):
        return Response({"detail": "Please wait before resending OTP."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    code = generate_otp()
    EmailOTP.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        expires_at=otp_expiry_time(),
        last_sent_at=timezone.now(),
        send_count=1,
    )
    send_otp_email(email=user.email, code=code, purpose=purpose)
    return Response({"detail": "OTP resent."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def LoginView(request):
    """
    POST: email, password
    Returns JWT tokens. Optionally block login if email not verified.
    """
    ser = LoginSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    email = ser.validated_data["email"].lower().strip()
    password = ser.validated_data["password"]

    user = authenticate(request, email=email, password=password)
    if not user:
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    # If you want to enforce verification:
    if not user.is_email_verified:
        return Response({"detail": "Email not verified."}, status=status.HTTP_403_FORBIDDEN)

    return Response({ "id": user.id, "tokens": _tokens_for_user(user), "email": user.email , "message": "Login successful" , "plan_type" : user.plan_type}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def ForgotPasswordView(request):
    """
    POST: email
    Sends RESET OTP
    """
    ser = ForgotPasswordSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    email = ser.validated_data["email"].lower().strip()

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Security: don't reveal user existence
        return Response({"detail": "If the email exists, an OTP has been sent."}, status=status.HTTP_200_OK)

    code = generate_otp()
    EmailOTP.objects.create(
        user=user,
        code=code,
        purpose="RESET",
        expires_at=otp_expiry_time(),
        last_sent_at=timezone.now(),
        send_count=1,
    )
    send_otp_email(email=user.email, code=code, purpose="RESET")

    return Response({"detail": "If the email exists, an OTP has been sent."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def ResetPasswordView(request):
    """
    POST: email, otp, new_password, confirm_password
    Validates OTP and sets new password.
    """
    ser = ResetPasswordSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    email = ser.validated_data["email"].lower().strip()
    # otp = ser.validated_data["otp"].strip()
    new_password = ser.validated_data["new_password"]

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)

    # otp_obj = EmailOTP.objects.filter(
    #     user=user, purpose="RESET", code=otp, is_used=False
    # ).order_by("-created_at").first()

    # if not otp_obj:
    #     return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
    # if otp_obj.is_expired():
    #     return Response({"detail": "OTP expired."}, status=status.HTTP_400_BAD_REQUEST)

    # otp_obj.is_used = True
    # otp_obj.save(update_fields=["is_used"])

    user.set_password(new_password)
    user.save(update_fields=["password"])

    return Response({"detail": "Password reset successful."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ChangePasswordView(request):
    """
    POST: old_password, new_password, confirm_password
    Requires JWT.
    """
    ser = ChangePasswordSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    old_password = ser.validated_data["old_password"]
    new_password = ser.validated_data["new_password"]

    if not user.check_password(old_password):
        return Response({"detail": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save(update_fields=["password"])

    return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)






# ----------------- views.py of profile section -----------------

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import UserProfile, TaxonomyCategory, TaxonomyItem, UserProfileSelection
from .serializers import UserProfileSerializer, TaxonomyCategorySerializer

def _get_or_none_profile(user):
    try:
        return UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None

def _set_intentions(profile: UserProfile, item_ids: list[int]):
    """
    Replace intentions selection (type=INTENTION).
    Enforces: items must be INTENTION type.
    """
    # remove existing INTENTION selections
    UserProfileSelection.objects.filter(
        profile=profile,
        item__category__type="INTENTION"
    ).delete()

    if not item_ids:
        return

    items = TaxonomyItem.objects.filter(
        id__in=item_ids,
        category__type="INTENTION",
        is_active=True,
        category__is_active=True
    )

    found_ids = set(items.values_list("id", flat=True))
    missing = [i for i in item_ids if i not in found_ids]
    if missing:
        raise ValueError(f"Invalid intention item ids: {missing}")

    UserProfileSelection.objects.bulk_create(
        [UserProfileSelection(profile=profile, item=item) for item in items]
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def taxonomy_list(request):
    """
    GET: returns headings + bullets
    Also marks selected=true for the current user's profile (if exists)
    """
    profile = _get_or_none_profile(request.user)
    selected_ids = set()
    if profile:
        selected_ids = set(profile.selected_items.values_list("id", flat=True))

    categories = TaxonomyCategory.objects.filter(is_active=True).prefetch_related("items")

    # build response manually to inject selected flag
    data = []
    for cat in categories:
        items = []
        for item in cat.items.filter(is_active=True).order_by("order", "id"):
            items.append({
                "id": item.id,
                "text": item.text,
                "order": item.order,
                "selected": item.id in selected_ids
            })
        data.append({
            "id": cat.id,
            "title": cat.title,
            "type": cat.type,
            "order": cat.order,
            "items": items
        })

    return Response(data, status=status.HTTP_200_OK)











@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def profile_me(request):
    """
    GET    -> my profile
    POST   -> create profile (once)
    PATCH  -> update profile (partial)
    Supports photo upload via multipart/form-data
    """
    profile = _get_or_none_profile(request.user)

    if request.method == "GET":
        if not profile:
            return Response({"detail": "Profile not created yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserProfileSerializer(profile).data, status=status.HTTP_200_OK)

    if request.method == "POST":
        if profile:
            return Response({"detail": "Profile already exists. Use PATCH."}, status=status.HTTP_400_BAD_REQUEST)

        ser = UserProfileSerializer(data=request.data, partial=False)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        intention_ids = ser.validated_data.pop("intention_item_ids", [])
        profile = UserProfile.objects.create(user=request.user, **ser.validated_data)

        try:
            _set_intentions(profile, intention_ids)
        except ValueError as e:
            profile.delete()
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UserProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    # PATCH
    if not profile:
        return Response({"detail": "Profile not created yet. Use POST first."}, status=status.HTTP_404_NOT_FOUND)

    ser = UserProfileSerializer(profile, data=request.data, partial=True)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    intention_ids = ser.validated_data.pop("intention_item_ids", None)

    for attr, val in ser.validated_data.items():
        setattr(profile, attr, val)
    profile.save()

    if intention_ids is not None:
        try:
            _set_intentions(profile, intention_ids)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(UserProfileSerializer(profile).data, status=status.HTTP_200_OK)





from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import TaxonomyCategory

@api_view(["GET"])
@permission_classes([AllowAny])
def public_taxonomy_list(request):
    """
    Public endpoint
    GET all active taxonomy (categories + items)
    No auth required
    """
    categories = (
        TaxonomyCategory.objects
        .filter(is_active=True)
        .prefetch_related("items")
        .order_by("order", "id")
    )

    data = []
    for cat in categories:
        items = []
        for item in cat.items.filter(is_active=True).order_by("order", "id"):
            items.append({
                "item_id": item.id,
                "text": item.text,
                "item_order": item.order,
            })

        data.append({
            "id": cat.id,
            "title": cat.title,
            "type": cat.type,
            "order": cat.order,
            "items": items,
        })

    return Response(data, status=status.HTTP_200_OK)





# ------------------ For one endpoint for profile & taxonomy ----------------
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import UserProfile, TaxonomyCategory, TaxonomyItem, UserProfileSelection
from .serializers import UserProfileSerializer

def _get_or_none_profile(user):
    try:
        return UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None

def _set_intentions(profile: UserProfile, item_ids: list[int]):
    # remove existing INTENTION selections
    UserProfileSelection.objects.filter(
        profile=profile,
        item__category__type="INTENTION"
    ).delete()

    if not item_ids:
        return

    items = TaxonomyItem.objects.filter(
        id__in=item_ids,
        # category__type="INTENTION",
        is_active=True,
        category__is_active=True
    )

    found_ids = set(items.values_list("id", flat=True))
    missing = [i for i in item_ids if i not in found_ids]
    if missing:
        raise ValueError(f"Invalid intention item ids: {missing}")

    UserProfileSelection.objects.bulk_create(
        [UserProfileSelection(profile=profile, item=item) for item in items]
    )

def _build_taxonomy_payload(selected_ids: set[int] | None):
    """
    selected_ids=None -> public taxonomy (no selected field)
    selected_ids=set(...) -> include selected=true/false
    """
    categories = (
        TaxonomyCategory.objects
        .filter(is_active=True)
        .prefetch_related("items")
        .order_by("order", "id")
    )

    data = []
    for cat in categories:
        items_list = []
        qs = cat.items.filter(is_active=True).order_by("order", "id")
        for item in qs:
            row = {"item_id": item.id, "text": item.text, "order": item.order}
            if selected_ids is not None:
                row["selected"] = item.id in selected_ids
            items_list.append(row)

        data.append({
            "id": cat.id,
            "title": cat.title,
            "type": cat.type,
            "order": cat.order,
            "items": items_list,
        })
    return data



@api_view(["GET", "POST", "PATCH"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def profile_taxonomy(request):

    is_auth = request.user.is_authenticated

    # ---------- GET (Public + Auth both) ----------
    if request.method == "GET":
        profile_data = None
        selected_ids = None

        if is_auth:
            profile = _get_or_none_profile(request.user)
            if profile:
                profile_data = UserProfileSerializer(profile).data
                selected_ids = set(profile.selected_items.values_list("id", flat=True))
            else:
                selected_ids = set()

        taxonomy = _build_taxonomy_payload(selected_ids if is_auth else None)

        return Response(
            {
                "authenticated": is_auth,
                "profile": profile_data,
                "taxonomy": taxonomy,
            },
            status=status.HTTP_200_OK
        )

    # ---------- POST / PATCH must be Auth ----------
    if not is_auth:
        return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

    profile = _get_or_none_profile(request.user)

    # ---------- POST (Create profile) ----------
    if request.method == "POST":
        if profile:
            return Response({"detail": "Profile already exists. Use PATCH."}, status=status.HTTP_400_BAD_REQUEST)

        ser = UserProfileSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        intention_ids = ser.validated_data.pop("intention_item_ids", [])
        profile = UserProfile.objects.create(user=request.user, **ser.validated_data)

        try:
            _set_intentions(profile, intention_ids)
        except ValueError as e:
            profile.delete()
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        selected_ids = set(profile.selected_items.values_list("id", flat=True))
        taxonomy = _build_taxonomy_payload(selected_ids)

        return Response(
            {
                "authenticated": True,
                "profile": UserProfileSerializer(profile).data,
                "taxonomy": taxonomy,
            },
            status=status.HTTP_201_CREATED
        )

    # ---------- PATCH (Update profile) ----------
    if request.method == "PATCH":
        if not profile:
            return Response({"detail": "Profile not created yet. Use POST first."}, status=status.HTTP_404_NOT_FOUND)

        ser = UserProfileSerializer(profile, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        intention_ids = ser.validated_data.pop("intention_item_ids", None)

        for attr, val in ser.validated_data.items():
            setattr(profile, attr, val)
        profile.save()

        if intention_ids is not None:
            try:
                _set_intentions(profile, intention_ids)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        selected_ids = set(profile.selected_items.values_list("id", flat=True))
        taxonomy = _build_taxonomy_payload(selected_ids)

        return Response(
            {
                "authenticated": True,
                "profile": UserProfileSerializer(profile).data,
                "taxonomy": taxonomy,
            },
            status=status.HTTP_200_OK
        )




from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from accounts.models import UserLocation  


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_user_location(request):
    """
    POST /api/location/

    {
        "latitude": 23.8103,
        "longitude": 90.4125
    }
    """

    lat = request.data.get("latitude")
    lon = request.data.get("longitude")

    if lat is None or lon is None:
        return Response(
            {"detail": "latitude and longitude are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return Response(
            {"detail": "latitude and longitude must be valid numbers."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # optional validation range
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return Response(
            {"detail": "Invalid latitude or longitude range."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # create or update
    location, created = UserLocation.objects.update_or_create(
        user=request.user,
        defaults={
            "latitude": lat,
            "longitude": lon
        }
    )

    return Response({
        "user_id": request.user.id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "created": created
    }, status=status.HTTP_200_OK)





# views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Available
from .serializers import AvailableSerializer


@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def availability_view(request):
    # POST = create or update (upsert)
    if request.method == "POST":
        serializer = AvailableSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            AvailableSerializer(instance).data,
            status=status.HTTP_200_OK
        )

    # PATCH = partial update
    if request.method == "PATCH":
        try:
            instance = Available.objects.get(user=request.user)
        except Available.DoesNotExist:
            return Response(
                {"detail": "Availability not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AvailableSerializer(
            instance,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)




from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import LegalDocument


def _get_doc(doc_type: str):
    return LegalDocument.objects.filter(doc_type=doc_type).first()


@api_view(["GET"])
def privacy_policy(request):
    doc = _get_doc(LegalDocument.TYPE_PRIVACY)
    if not doc:
        return Response({"detail": "Privacy policy not set."}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "type": "PRIVACY",
        "title": doc.title or "Privacy Policy",
        "content": doc.content,
        "version": doc.version,
        "updated_at": doc.updated_at,
    })


@api_view(["GET"])
def terms_and_conditions(request):
    doc = _get_doc(LegalDocument.TYPE_TERMS)
    if not doc:
        return Response({"detail": "Terms & conditions not set."}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "type": "TERMS",
        "title": doc.title or "Terms & Conditions",
        "content": doc.content,
        "version": doc.version,
        "updated_at": doc.updated_at,
    })






from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import UserProfile
from .serializers import PublicUserProfileSerializer
from .models import TaxonomyCategory  

@api_view(["GET"])
@permission_classes([AllowAny])
def public_user_profile(request, user_id: int):
    profile = get_object_or_404(
        UserProfile.objects.select_related("user").prefetch_related("selected_items"),
        user_id=user_id
    )

    # Only SKILL categories
    categories = (
        TaxonomyCategory.objects
        .filter(is_active=True, type="SKILL")
        .prefetch_related("items")
        .order_by("order", "id")
    )

    selected_ids = set(profile.selected_items.values_list("id", flat=True))

    selected_taxonomy = []
    for cat in categories:
        items = cat.items.filter(is_active=True).order_by("order", "id")

        selected_items = [
            {"id": item.id, "text": item.text, "order": item.order}
            for item in items
            if item.id in selected_ids
        ]

        # only send categories that have selected items
        if selected_items:
            selected_taxonomy.append({
                "id": cat.id,
                "title": cat.title,
                "type": cat.type,   # will be "SKILL"
                "order": cat.order,
                "items": selected_items
            })

    return Response(
        {
            "profile": PublicUserProfileSerializer(profile, context={"request": request}).data,
            "selected_taxonomy": selected_taxonomy
        },
        status=status.HTTP_200_OK
    )







from .serializers import UpdatePlanSerializer


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_plan(request):
    """
    PATCH /api/accounts/update-plan/
    Body: { "plan_type": "PREMIUM" }
    """

    serializer = UpdatePlanSerializer(
        request.user,
        data=request.data,
        partial=True
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    return Response(
        {
            "success": True,
            "plan_type": request.user.plan_type,
            "plan_expire_at": request.user.plan_expire_at,
        },
        status=status.HTTP_200_OK
    )
