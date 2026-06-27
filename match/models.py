from django.conf import settings
from django.db import models
from django.db.models import Q


class Match(models.Model):
    """
    Mutual LIKE => a connection between two users.
    Always store smaller user_id in user1, larger in user2 (ordered pair).
    """
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matches_as_user1")
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matches_as_user2")

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    unmatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(user1=models.F("user2")), name="no_self_match"),
            models.UniqueConstraint(fields=["user1", "user2"], name="uniq_match_pair"),
        ]
        indexes = [
            models.Index(fields=["user1", "created_at"]),
            models.Index(fields=["user2", "created_at"]),
        ]

    def __str__(self):
        return f"Match({self.user1_id}, {self.user2_id})"


class Conversation(models.Model):
    """
    1-to-1 room for a match.
    """
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name="conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Conversation(match={self.match_id})"


class Message(models.Model):
    TYPE_TEXT = "TEXT"
    TYPE_CHOICES = (
        (TYPE_TEXT, "TEXT"),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")

    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_TEXT)
    text = models.TextField(blank=True)
    is_seen = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)


    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]

    def __str__(self):
        return f"Msg({self.id}) conv={self.conversation_id}"


class Notification(models.Model):
    TYPE_LIKE = "LIKE"
    TYPE_MATCH = "MATCH"
    TYPE_MESSAGE = "MESSAGE"

    TYPE_CHOICES = (
        (TYPE_LIKE, "LIKE"),
        (TYPE_MATCH, "MATCH"),
        (TYPE_MESSAGE, "MESSAGE"),
    )

    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="notifications_sent"
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120, blank=True)
    body = models.CharField(max_length=255, blank=True)

    data = models.JSONField(default=dict, blank=True)  # match_id, conversation_id, message_id etc
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["to_user", "is_read", "created_at"]),
            models.Index(fields=["to_user", "created_at"]),
        ]

    def __str__(self):
        return f"Notif({self.type}) to={self.to_user_id}"


class DeviceToken(models.Model):
    PLATFORM_ANDROID = "ANDROID"
    PLATFORM_IOS = "IOS"
    PLATFORM_WEB = "WEB"
    PLATFORM_CHOICES = (
        (PLATFORM_ANDROID, "ANDROID"),
        (PLATFORM_IOS, "IOS"),
        (PLATFORM_WEB, "WEB"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DeviceToken({self.user_id}, {self.platform})"

# This is a comment line 