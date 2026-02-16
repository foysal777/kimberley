from django.urls import path
from .views import (
    RegisterView,
    VerifyOTPView,
    LoginView,
    ResendOTPView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    privacy_policy,
    profile_me,
    profile_taxonomy,
    public_taxonomy_list,
    save_user_location,
    taxonomy_list,
    terms_and_conditions,
    availability_view
)

urlpatterns = [
    # Auth / Registration
    path("register/", RegisterView, name="register"),
    path("verify-otp/", VerifyOTPView, name="verify-otp"),
    path("resend-otp/", ResendOTPView, name="resend-otp"),
    path("login/", LoginView, name="login"),
    # Password management
    path("forgot-password/", ForgotPasswordView, name="forgot-password"),
    path("reset-password/", ResetPasswordView, name="reset-password"),
    path("change-password/", ChangePasswordView, name="change-password"),

    path("profile/", profile_me, name="profile-me"), # cancel 
    path("taxonomy/", taxonomy_list, name="taxonomy"), # cancel 
    path("taxonomy/public/", public_taxonomy_list, name="taxonomy-public"), #all public taxonomy list ( for dropdowns in frontend )
    path("user-profile/", profile_taxonomy, name="profile-taxonomy"),  
    path("privacy-policy/", privacy_policy, name="privacy-policy"),
    path("terms/", terms_and_conditions, name="terms-and-conditions"),
    path("location/", save_user_location, name="save-user-location"),
    path("availability/", availability_view, name="availability"),

]



