from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CheckEmailVerificationView, EnforceUserPasswordReset, GoogleLoginView, PasswordResetConfirmView, PasswordResetRequestView, ResendEmailVerificationApiView, VerifyPhoneView,UserViewSet, RegisterView, LoginView, VerifyEmailView, logout_view, csrf_view, user_detail, VerifyCaptchaView
from rest_framework_simplejwt import views as jwt_views

router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('verify-email/<str:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification-email/', ResendEmailVerificationApiView.as_view(), name='resend-email-verification'),
    path('user/', user_detail, name='user-detail'),
    path('csrf/', csrf_view, name='csrf'),
    path('token/', jwt_views.TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
    path('', include(router.urls)),  # Include the router's URLs
    path('verify_recaptcha/', VerifyCaptchaView.as_view(), name="verify_recaptcha"),
    path('verify-phone/', VerifyPhoneView.as_view(), name='verify-phone'),
    path('google/login/', GoogleLoginView.as_view(), name='google_login'),
    path('check_email_verification/', CheckEmailVerificationView.as_view(), name="check_email_verification"),
    path('reset-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('reset-password/<uuid:token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('enforce_password_reset', EnforceUserPasswordReset.as_view(), name="enforce_password_reset"), #just in case

]
