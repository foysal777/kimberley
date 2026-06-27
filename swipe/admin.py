from django.contrib import admin
from .models import SwipeAction

@admin.register(SwipeAction)
class SwipeActionAdmin(admin.ModelAdmin):
    list_display = ("id", "get_from_user_email", "get_to_user_email", "action", "created_at", "updated_at")
    search_fields = ("from_user__email", "to_user__email", "action")
    list_filter = ("action", "created_at", "updated_at")

    def get_from_user_email(self, obj):
        return obj.from_user.email
    get_from_user_email.short_description = 'From User'

    def get_to_user_email(self, obj):
        return obj.to_user.email
    get_to_user_email.short_description = 'To User'
