from rest_framework import serializers
from match.models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender_id",
            "message_type",
            "text",
            "is_seen",
            "is_delivered",
            "created_at",
            "read_at",
        ]
        read_only_fields = fields
