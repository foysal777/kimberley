from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SwipeAction

User = get_user_model()


class SwipeActionCreateSerializer(serializers.ModelSerializer):
    to_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SwipeAction
        fields = ["to_user_id", "action"]

    def validate_to_user_id(self, value):
        request = self.context["request"]
        if request.user.id == value:
            raise serializers.ValidationError("You cannot swipe yourself.")
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Target user does not exist.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        to_user_id = validated_data.pop("to_user_id")
        to_user = User.objects.get(id=to_user_id)

        # If already exists, update action instead of error (MVP friendly)
        obj, created = SwipeAction.objects.update_or_create(
            from_user=request.user,
            to_user=to_user,
            defaults={"action": validated_data["action"]},
        )
        return obj


class SwipeActionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwipeAction
        fields = ["id", "from_user", "to_user", "action", "created_at"]
        read_only_fields = fields
