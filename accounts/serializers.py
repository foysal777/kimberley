from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(data["password"])
        return data


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=["REGISTER", "RESET"])


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=["REGISTER", "RESET"])


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(data["new_password"])
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(data["new_password"])
        return data



# --------------- profile serializers ----------------

from rest_framework import serializers
from .models import Available, UserProfile, TaxonomyCategory, TaxonomyItem, UserProfileSelection

class TaxonomyItemSerializer(serializers.ModelSerializer):
    selected = serializers.BooleanField(read_only=True)

    class Meta:
        model = TaxonomyItem
        fields = ["id", "text", "order", "selected"]


class TaxonomyCategorySerializer(serializers.ModelSerializer):
    items = TaxonomyItemSerializer(many=True, read_only=True)

    class Meta:
        model = TaxonomyCategory
        fields = ["id", "title", "type", "order", "items"]


import json
from django.http import QueryDict
from rest_framework import serializers
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    intention_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "photo",
            "full_name",
            "role",
            "industry",
            "location",
            "what_hoping_to_gain",
            "bio",
            "available_days",
            "time_start",
            'time_end',
            "intention_item_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


    def validate(self, data):
        start = data.get("time_start")
        end = data.get("time_end")

        if start and end:
            if start >= end:
                raise serializers.ValidationError(
                    "time_end must be greater than time_start"
                )
        return data
    



  


    def to_internal_value(self, data):
        """
        Handles multipart/form-data (QueryDict) + JSONField/ListField.
        Accepts:
          available_days = ["Mon","Wed"]  (string) OR repeated keys
          intention_item_ids = [1,2]     (string) OR repeated keys
        """
        # ✅ QueryDict -> mutable dict
        if isinstance(data, QueryDict):
            mutable = data.copy()  # still QueryDict
            # convert QueryDict into plain dict but keep getlist behavior
            plain = {}
            for k in mutable.keys():
                vals = mutable.getlist(k)
                plain[k] = vals if len(vals) > 1 else mutable.get(k)
            data = plain
        else:
            data = dict(data)

        # ---------- available_days ----------
        days = data.get("available_days")

        # if it came as list already (multiple keys)
        if isinstance(days, list):
            data["available_days"] = days
        elif isinstance(days, str):
            s = days.strip()
            # try JSON list
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        data["available_days"] = parsed
                    else:
                        data["available_days"] = []
                except json.JSONDecodeError:
                    raise serializers.ValidationError({
                        "available_days": "Value must be valid JSON array like [\"Mon\",\"Wed\"]."
                    })
            else:
                # fallback "Mon,Wed"
                data["available_days"] = [x.strip() for x in s.split(",") if x.strip()]

        # ---------- intention_item_ids ----------
        ids = data.get("intention_item_ids")

        if isinstance(ids, list):
            try:
                data["intention_item_ids"] = [int(x) for x in ids]
            except (TypeError, ValueError):
                raise serializers.ValidationError({
                    "intention_item_ids": "All values must be integers."
                })

        elif isinstance(ids, str):
            s = ids.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)   # expects [1,2]
                except json.JSONDecodeError:
                    raise serializers.ValidationError({
                        "intention_item_ids": "Value must be valid JSON array like [1,2]."
                    })
                if not isinstance(parsed, list):
                    raise serializers.ValidationError({
                        "intention_item_ids": "Must be a list like [1,2]."
                    })
                try:
                    data["intention_item_ids"] = [int(x) for x in parsed]
                except (TypeError, ValueError):
                    raise serializers.ValidationError({
                        "intention_item_ids": "All values must be integers."
                    })
            else:
                # fallback "1,2"
                try:
                    data["intention_item_ids"] = [int(x.strip()) for x in s.split(",") if x.strip()]
                except ValueError:
                    raise serializers.ValidationError({
                        "intention_item_ids": "Send like [1,2] or 1,2"
                    })

        return super().to_internal_value(data)









class AvailableSerializer(serializers.ModelSerializer):
    is_available = serializers.BooleanField(required=False)
    is_visible = serializers.BooleanField(required=False)

    class Meta:
        model = Available
        fields = ["is_available", "is_visible"]

    def create(self, validated_data):
        user = self.context["request"].user

        instance, created = Available.objects.get_or_create(
            user=user,
            defaults=validated_data
        )

        
        if not created:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

        return instance

    def update(self, instance, validated_data):
      
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance







from rest_framework import serializers
from .models import UserProfile

class PublicUserProfileSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "photo",
            "full_name",
            "role",
            "industry",
            "location",
            "what_hoping_to_gain",
            "bio",
            "available_days",
            "time_start",
            "time_end",
        ]
        read_only_fields = fields

    def get_photo(self, obj):
        request = self.context.get("request")
        if not obj.photo:
            return None
        if request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url





from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import User


class UpdatePlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["plan_type"]

    def validate_plan_type(self, value):
        valid_plans = [choice[0] for choice in User.PLAN_CHOICES]
        if value not in valid_plans:
            raise serializers.ValidationError("Invalid plan type.")
        return value

    def update(self, instance, validated_data):
        new_plan = validated_data.get("plan_type")

        instance.plan_type = new_plan

 
        if new_plan == User.PLAN_PREMIUM:
            instance.plan_expire_at = timezone.now() + timedelta(days=30)
        else:
            instance.plan_expire_at = None

        instance.save(update_fields=["plan_type", "plan_expire_at"])
        return instance



from rest_framework import serializers
from .models import SupportTicket

class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["email", "message"]

    def validate_message(self, value):
        if len((value or "").strip()) < 5:
            raise serializers.ValidationError("Please describe your problem.")
        return value


class ReportUserSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)

