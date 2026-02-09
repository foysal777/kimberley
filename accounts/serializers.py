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
    otp = serializers.CharField(max_length=6)
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
from .models import UserProfile, TaxonomyCategory, TaxonomyItem, UserProfileSelection

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
            "time_range",
            "intention_item_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

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


 