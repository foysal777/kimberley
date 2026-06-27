from django.contrib import admin
from .models import Match, Conversation, Message, Notification

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "get_user1_email", "get_user2_email", "is_active", "created_at", "unmatched_at")
    search_fields = ("user1__email", "user2__email")
    list_filter = ("is_active", "created_at", "unmatched_at")

    def get_user1_email(self, obj):
        return obj.user1.email
    get_user1_email.short_description = 'User 1 Email'

    def get_user2_email(self, obj):
        return obj.user2.email
    get_user2_email.short_description = 'User 2 Email'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "get_match_description", "created_at", "last_message_at")
    search_fields = ("match__user1__email", "match__user2__email")
    list_filter = ("created_at", "last_message_at")

    def get_match_description(self, obj):
        return f"Match {obj.match.id}: {obj.match.user1.email} & {obj.match.user2.email}"
    get_match_description.short_description = 'Match Description'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation_id", "get_sender_email", "message_type", "get_short_text", "is_seen", "is_delivered", "created_at")
    search_fields = ("conversation__id", "sender__email", "text")
    list_filter = ("message_type", "is_seen", "is_delivered", "created_at")

    def get_sender_email(self, obj):
        return obj.sender.email
    get_sender_email.short_description = 'Sender'

    def get_short_text(self, obj):
        return obj.text[:50] + ("..." if len(obj.text) > 50 else "")
    get_short_text.short_description = 'Message Content'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "get_to_user_email", "get_from_user_email", "type", "title", "body", "is_read", "created_at")
    search_fields = ("to_user__email", "from_user__email", "type", "title")
    list_filter = ("type", "is_read", "created_at")

    def get_to_user_email(self, obj):
        return obj.to_user.email
    get_to_user_email.short_description = 'Recipient'

    def get_from_user_email(self, obj):
        return obj.from_user.email if obj.from_user else 'System'
    get_from_user_email.short_description = 'Sender'
