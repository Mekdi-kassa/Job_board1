# user/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import transaction
from django.conf import settings
from .models import User
from .utils import send_verification_email
from .validators import validate_password_strength
import bleach


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        min_length=8
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    role = serializers.ChoiceField(choices=User.Role.choices)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'username', 'role', 'password', 'confirm_password']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'username': {'required': False, 'allow_blank': True, 'allow_null': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        # Enforce strong password
        validate_password_strength(attrs['password'])
        
        email = attrs.get('email', '').lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        
        # Sanitize inputs
        attrs['first_name'] = bleach.clean(attrs.get('first_name', ''), tags=[], strip=True)
        attrs['last_name'] = bleach.clean(attrs.get('last_name', ''), tags=[], strip=True)
        attrs['email'] = email
        
        # Handle username: if empty string, set to None
        if 'username' in attrs and attrs['username'] == '':
            attrs['username'] = None
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        role = validated_data.get('role')
        
        # If username is empty or None, generate from email
        username = validated_data.get('username')
        if not username:
            # Create username from email (remove @ and special chars)
            username = validated_data['email'].split('@')[0]
            # Remove any special characters
            import re
            username = re.sub(r'[^a-zA-Z0-9_]', '', username)
            # Make it unique if needed
            if User.objects.filter(username=username).exists():
                import uuid
                username = f"{username}_{uuid.uuid4().hex[:6]}"
            validated_data['username'] = username
        
        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            username=validated_data.get('username'),
            role=role,
            is_active=False,  # User must verify email first
            is_verified=False,
        )
        
        # Send verification email
        if settings.EMAIL_VERIFICATION_REQUIRED:
            try:
                success, message = send_verification_email(user)
                if not success:
                    print(f"Email dispatch notice: {message}")
            except Exception as e:
                print(f"Email dispatch error: {e}")
        
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password', '')
        
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError({"email": "Invalid email or password."})
        
        if user.is_suspended:
            raise serializers.ValidationError({"email": "This account has been suspended."})
        
        # Check if email is verified
        if not user.is_verified:
            # Check if token expired, resend if needed
            if user.is_email_verification_expired():
                # Resend verification email
                success, message = send_verification_email(user)
                if success:
                    raise serializers.ValidationError({
                        "email": "Your verification link expired. We have sent a new one to your email."
                    })
                else:
                    raise serializers.ValidationError({
                        "email": "Please verify your email before logging in. Check your inbox for the verification link."
                    })
            raise serializers.ValidationError({
                "email": "Please verify your email before logging in. Check your inbox for the verification link."
            })
        
        if not user.is_active:
            raise serializers.ValidationError({"email": "This account is inactive."})
        
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError({"password": "Invalid email or password."})
        
        refresh = RefreshToken.for_user(user)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        token = attrs.get('token', '')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})
        
        if user.is_verified:
            raise serializers.ValidationError({"email": "Email already verified."})
        
        attrs['user'] = user
        attrs['token'] = token
        
        return attrs


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})
        
        if user.is_verified:
            raise serializers.ValidationError({"email": "Email already verified."})
        
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'username', 'role', 'is_verified', 'is_suspended', 'created_at']
        read_only_fields = ['id', 'is_verified', 'is_suspended', 'created_at']


from rest_framework_simplejwt.serializers import TokenRefreshSerializer

class RefreshTokenSerializer(TokenRefreshSerializer):
    """Refresh JWT access token serializer"""
    pass


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower().strip()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError("No account found with this email address.")
        return email


class ResetPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=255)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        # Enforce strong password
        validate_password_strength(attrs['new_password'])

        email = attrs.get('email', '').lower().strip()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError({"email": "No account found with this email address."})
        
        attrs['user'] = user
        return attrs