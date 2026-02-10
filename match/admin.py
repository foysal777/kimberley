from django.contrib import admin
from  .models import Match, Conversation, Message, Notification


admin.site.register(Match)
admin.site.register(Conversation)       
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation_id", "sender_id")
    search_fields = ("conversation__id", "sender__email", "content")
   




@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "to_user_id", "from_user_id", "type", "created_at", "is_read")
    search_fields = ("to_user__email", "from_user__email", "type")
    list_filter = ("type", "is_read", "created_at")




