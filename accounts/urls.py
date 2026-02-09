from django.urls import path
from .views import (
    RegisterView,
    VerifyOTPView,
    LoginView,
    ResendOTPView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    profile_me,
    profile_taxonomy,
    public_taxonomy_list,
    taxonomy_list,
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

]



