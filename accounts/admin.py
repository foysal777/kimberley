from django.contrib import admin
from .models import User, EmailOTP , UserProfile ,  UserProfileSelection , TaxonomyCategory , TaxonomyItem  , UserLocation , Available , LegalDocument




@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "doc_type", "title", "version", "updated_at")
    search_fields = ("doc_type", "title")
    list_filter = ("doc_type", "updated_at")




@admin.register(Available)
class AvailableAdmin(admin.ModelAdmin):
    list_display = ("id", "user__email", "is_available", "is_visible")
    search_fields = ("user__email",)
    list_filter = ("is_available", "is_visible")


@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ("id","user__email", "user_id", "latitude", "longitude")
    search_fields = ("user__email",)
    list_filter = ("user__email",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "username", "is_email_verified", "is_staff", "is_active")
    search_fields = ("email", "username")
    list_filter = ("is_email_verified", "is_staff", "is_active")

admin.site.register(EmailOTP)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "full_name", "user__email", "created_at", )
    search_fields = ("full_name", "user__email")
    list_filter = ("created_at", "updated_at")


@admin.register(UserProfileSelection)
class UserProfileSelectionAdmin(admin.ModelAdmin):
    list_display = ("id", "profile_id", "item_id")
    search_fields = ("profile__full_name", "item__text")
    list_filter = ("profile__full_name", "item__text")  


@admin.register(TaxonomyCategory)
class TaxonomyCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "type", "order", "is_active")
    search_fields = ("title",)
    list_filter = ("type", "is_active")



@admin.register(TaxonomyItem)
class TaxonomyItemAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "text", "order")
    search_fields = ("text",)
    list_filter = ("category",)


# Register your models here.
