from django.contrib import admin
from .models import (
    User, EmailOTP, UserProfile, UserProfileSelection, 
    TaxonomyCategory, TaxonomyItem, UserLocation, Available, 
    LegalDocument, SupportTicket, UserReport, UserBlock, ProfileView
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "username", "plan_type", "is_email_verified", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    list_filter = ("plan_type", "is_email_verified", "is_staff", "is_active", "date_joined")
    ordering = ("-id",)

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("id", "get_user_email", "code", "purpose", "created_at", "expires_at", "is_used")
    search_fields = ("user__email", "code")
    list_filter = ("purpose", "is_used", "created_at")
    
    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "get_user_email", "full_name", "role", "industry", "location", "is_online", "created_at")
    search_fields = ("full_name", "user__email", "role", "industry", "location")
    list_filter = ("is_online", "created_at", "updated_at")

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'

@admin.register(TaxonomyCategory)
class TaxonomyCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "type", "order", "is_active")
    search_fields = ("title",)
    list_filter = ("type", "is_active")
    ordering = ("order", "id")

@admin.register(TaxonomyItem)
class TaxonomyItemAdmin(admin.ModelAdmin):
    list_display = ("id", "get_category_title", "text", "order", "is_active")
    search_fields = ("text", "category__title")
    list_filter = ("category", "is_active")
    ordering = ("category", "order", "id")

    def get_category_title(self, obj):
        return obj.category.title
    get_category_title.short_description = 'Category'

@admin.register(UserProfileSelection)
class UserProfileSelectionAdmin(admin.ModelAdmin):
    list_display = ("id", "get_profile_name", "get_item_text", "created_at")
    search_fields = ("profile__full_name", "profile__user__email", "item__text")
    list_filter = ("item__category", "created_at")

    def get_profile_name(self, obj):
        return obj.profile.full_name or obj.profile.user.email
    get_profile_name.short_description = 'Profile / Email'

    def get_item_text(self, obj):
        return obj.item.text
    get_item_text.short_description = 'Taxonomy Item'

@admin.register(ProfileView)
class ProfileViewAdmin(admin.ModelAdmin):
    list_display = ("id", "get_viewer_email", "get_viewed_email", "created_at")
    search_fields = ("viewer__email", "viewed_user__email")
    list_filter = ("created_at",)

    def get_viewer_email(self, obj):
        return obj.viewer.email
    get_viewer_email.short_description = 'Viewer'

    def get_viewed_email(self, obj):
        return obj.viewed_user.email
    get_viewed_email.short_description = 'Viewed User'

@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ("id", "get_user_email", "latitude", "longitude")
    search_fields = ("user__email",)

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'

@admin.register(Available)
class AvailableAdmin(admin.ModelAdmin):
    list_display = ("id", "get_user_email", "is_available", "is_visible")
    search_fields = ("user__email",)
    list_filter = ("is_available", "is_visible")

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'

@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "doc_type", "title", "version", "updated_at")
    search_fields = ("doc_type", "title")
    list_filter = ("doc_type", "updated_at")

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "get_user_email", "email", "message", "created_at")
    search_fields = ("user__email", "email", "message")
    list_filter = ("created_at",)

    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    get_user_email.short_description = 'User Email'

@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ("id", "get_reporter_email", "get_reported_email", "reason", "created_at")
    search_fields = ("reporter__email", "reported_user__email", "reason")
    list_filter = ("created_at",)

    def get_reporter_email(self, obj):
        return obj.reporter.email
    get_reporter_email.short_description = 'Reporter'

    def get_reported_email(self, obj):
        return obj.reported_user.email
    get_reported_email.short_description = 'Reported User'

@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "get_blocker_email", "get_blocked_email", "created_at")
    search_fields = ("blocker__email", "blocked_user__email")
    list_filter = ("created_at",)

    def get_blocker_email(self, obj):
        return obj.blocker.email
    get_blocker_email.short_description = 'Blocker'

    def get_blocked_email(self, obj):
        return obj.blocked_user.email
    get_blocked_email.short_description = 'Blocked User'
