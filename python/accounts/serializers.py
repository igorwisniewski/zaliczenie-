from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from .models import MyUser

User = get_user_model()


class CheckEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'confirm_password', 'phone_number')

    def validate(self, data):
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError({"confirm_password": "Passwords must match."})
        else:
            raise serializers.ValidationError("Both password and confirm_password are required.")

        if 'phone_number' not in data:
            raise serializers.ValidationError({"phone_number": "Phone number is required."})
        
        phone_number = data['phone_number']
        if not phone_number:
            raise serializers.ValidationError({"phone_number": "Phone number cannot be empty."})
        if not phone_number.startswith('+'):
            raise serializers.ValidationError({"phone_number": "Phone number must start with '+'."})

        return data


    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            phone_number=validated_data['phone_number']
        )
        user.is_verified = False
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    #def validate(self, data):
    #    user = User.objects.get(email = email)
    #    if user and user.is_active:
    #        return user
    #    raise serializers.ValidationError("Invalid credentials")
    

class EmailVerificationResendSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EnforceUserPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'is_active', 'is_staff', 'is_superuser')

class UserSerializerAdmin(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'is_phone_verified', 'phone_number')

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'is_verified', 'is_phone_verified', 'phone_number')

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            is_verified=validated_data['is_verified'],
            is_phone_verified=validated_data['is_phone_verified'],
            phone_number=validated_data['phone_number']
        )
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'is_phone_verified', 'phone_number')

class UserDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id']


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    #token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)