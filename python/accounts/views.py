from datetime import timedelta
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout, authenticate
from rest_framework import  viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .utils import send_verification_code_email
from .serializers import CheckEmailVerificationSerializer, EmailVerificationResendSerializer, EnforceUserPasswordResetSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer, RegisterSerializer, LoginSerializer, UserSerializer, UserCreateSerializer, UserSerializerAdmin, UserUpdateSerializer, UserDeleteSerializer
from django.http import JsonResponse
from django.middleware.csrf import get_token
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, TokenError
from .models import MyUser, PasswordResetToken
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
import requests
from django.utils import timezone



secret_key = settings.GOOGLE_RECAPTCHA_SECRET_KEY


class isStaffUser(BasePermission):
    def has_permission(self, request, view):
         user = request.user
         return user.is_staff


class VerifyCaptchaView(APIView):
    permission_classes = [AllowAny]


    def post(self, request):
        if request.data.get('g-recaptcha-response') is None:
            return Response(data={'error': 'Invalid ReCAPTCHA'}, status=status.HTTP_400_BAD_REQUEST)
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data={
            'secret': secret_key,
            "response": request.data['g-recaptcha-response']
        })
        if r.json()['success']:
            return Response(data={'detail': 'ReCAPTCHA verified.'}, status=status.HTTP_200_OK)
        return Response({'detail': 'ReCAPTCHA error'}, status=status.HTTP_400_BAD_REQUEST)
        


def csrf_view(request):
    return JsonResponse({'csrfToken': get_token(request)})

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response(
                    {"message": "User created successfully. Please check your email to verify your account."},
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {"error": "An unexpected error occurred during user creation.", "error_msg": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = MyUser.objects.get(email=serializer.validated_data["email"])
            except MyUser.DoesNotExist:
                raise AuthenticationFailed("Account does not exist")
            if user is None:
                raise AuthenticationFailed("User does not exist")
            if not user.is_verified:
                raise AuthenticationFailed("Email not verified")
            if not user.is_phone_verified:
                raise AuthenticationFailed("Verify your phone number")
            if user.password_reset_required:
                raise AuthenticationFailed("Reset your password!")
            if not user.check_password(serializer.validated_data["password"]):
                raise AuthenticationFailed("Incorrect Password")
            access_token = AccessToken.for_user(user)
            refresh_token = RefreshToken.for_user(user)
            return Response({"message": "Login successful", "accessToken": str(access_token), "refreshToken": str(refresh_token)}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token, *args, **kwargs):
        try:
            user = MyUser.objects.get(email_verification_token=token)
            if user.is_verified:
                return Response({"message": "User is already verified"}, status=status.HTTP_200_OK)
            if user.email_verification_expiry > timezone.now():
                user.is_verified = True
                user.is_active = True
                user.email_verification_token = None
                user.email_verification_expiry = None
                user.save()
                return Response({"message": f"Email {user.email} verified successfully"}, status=status.HTTP_200_OK)
            return Response({"message": "Verification token has expired"}, status=status.HTTP_400_BAD_REQUEST)
        except MyUser.DoesNotExist:
            return Response({"message": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        

class ResendEmailVerificationApiView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = EmailVerificationResendSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = MyUser.objects.get(email=serializer.validated_data["email"])
                if user.is_verified:
                    return Response({"message": "User is already verified"}, status=status.HTTP_400_BAD_REQUEST)
                if user.email_verification_expiry > timezone.now():
                    return Response({"message": "Verification token has not expired yet"}, status=status.HTTP_400_BAD_REQUEST)
                user.email_verification_token = None
                user.save()
                send_verification_code_email(user)
                return Response({"message": "Verification email has been resent"}, status=status.HTTP_200_OK)
            except MyUser.DoesNotExist:
                return Response({'message': 'User does not exist!'}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data['refresh_token']
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({"message": "Logout successful"})
    except TokenError:
        raise AuthenticationFailed("Invalid Token")
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request):
    user = request.user
    return Response({'username': user.username, 'is_superuser': user.is_superuser, 'is_staff': user.is_staff})



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated & isStaffUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'destroy':
            return UserDeleteSerializer
        return UserSerializerAdmin

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if not self.has_permission_to_delete(request, instance):
            raise PermissionDenied("You do not have permission to delete this user.")

        self.perform_destroy(instance)
        return Response({'detail': 'User deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)

    def has_permission_to_delete(self, request, instance):
        """
        Custom permission check to determine if the user is allowed to delete the given instance.
        """
        return request.user.is_staff or request.user.is_superuser
    
class VerifyPhoneView(APIView):

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        try:
            user = MyUser.objects.filter(email=email)[0]
            if not user.check_password(str(password)):
                return Response({"message": "User does not exist!"}, status=status.HTTP_401_UNAUTHORIZED)   
            if not user.phone_number:
                return Response({"message": "Phone number is not provided"}, status=status.HTTP_400_BAD_REQUEST)
            if user.is_phone_verified:
                return Response({"message": "User is already verified!"}, status=status.HTTP_400_BAD_REQUEST)
            code = request.data.get('code')
            if not code:
                return Response({"message": "Verification code is required"}, status=status.HTTP_400_BAD_REQUEST)
            if user.phone_verification_code == code:
                user.is_phone_verified = True
                user.phone_verification_code = ""
                user.save()
                return Response({"message": "Phone number verified successfully"}, status=status.HTTP_200_OK)
            return Response({"message": "Invalid verification code"}, status=status.HTTP_400_BAD_REQUEST)
        except MyUser.DoesNotExist:
             return Response({"message": "User does not exist!"}, status=status.HTTP_401_UNAUTHORIZED)


class CheckEmailVerificationView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = CheckEmailVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'message': "Aint valid, dawg"}, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        try:
            user = MyUser.objects.filter(email=email)[0]
            if not user.check_password(password):
                return Response({"message": "User does not exist!"}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({'is_verified': user.is_verified}, status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
             return Response({"message": "User does not exist!"}, status=status.HTTP_401_UNAUTHORIZED)
        

class PasswordResetRequestView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = MyUser.objects.get(email=serializer.validated_data['email'])
                
                token = uuid.uuid4()
                expiry = timezone.now() + timedelta(hours=1)
                PasswordResetToken.objects.create(user=user, token=token, expiry=expiry)
                
                reset_url = f"https://cncgart.pl/reset-password/{token}/"
                template_name = "email_templates/reset_password.html"

                context = {
                    "reset_url": reset_url,
                    "username": user.username,
                    "email": user.email,
                }

                html_content = render_to_string(template_name, context)
                try:
                    send_mail(
                        subject='Password Reset Request',
                        message=f'Click the link to reset your password: {reset_url}',
                        recipient_list=[user.email],
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        fail_silently=False,
                        html_message=html_content,
                    )
                except Exception as e:
                    print(str(e))
                return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
            except MyUser.DoesNotExist:
                return Response({"message": "Email not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PasswordResetConfirmView(APIView):
    def post(self, request, token, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            #token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            try:
                reset_token = PasswordResetToken.objects.get(token=token)
                if reset_token.is_expired():
                    return Response({"message": "Token has expired."}, status=status.HTTP_400_BAD_REQUEST)
                user = reset_token.user
                if user.password_reset_required:
                    user.password_reset_required = False
                user.set_password(new_password)
                user.save()
                reset_token.delete()
                return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)
            except PasswordResetToken.DoesNotExist:
                return Response({"message": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EnforceUserPasswordReset(APIView):
    permission_classes = [IsAuthenticated&isStaffUser]
    def post(self, request, token, *args, **kwargs):
        serializer = EnforceUserPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = MyUser.objects.all().filter(email=serializer.validated_data["email"])[0]
                user.password_reset_required = True
                user.save()
                return Response({"message": "Enforced password user reset!"}, status=status.HTTP_200_OK)
            except MyUser.DoesNotExist:
                return Response({"message": "User doesnt exist!"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the token with Google
        google_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        response = requests.get(google_url)
        if response.status_code != 200:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        user_data = response.json()
        email = user_data.get("email")
        name = user_data.get('name')
        familyName = user_data.get('family_name')

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create(
                email=email,
                username=f"{name}_{familyName}",
                is_verified=True,
                is_active=True
            )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({
            "refreshToken": str(refresh),
            "accessToken": str(access)
        }, status=status.HTTP_200_OK)




def csrf_view(request):
    return JsonResponse({'csrfToken': get_token(request)})

User = get_user_model()
