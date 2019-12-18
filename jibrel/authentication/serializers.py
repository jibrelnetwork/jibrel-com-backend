from typing import (
    Any,
    Optional
)

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from jibrel.authentication.models import (
    Profile,
    User
)
from jibrel.core.rest_framework import (
    AlwaysTrueFieldValidator,
    LanguageField
)
from jibrel.core.serializers import PasswordField


class CaseInsensitiveEmailField(serializers.EmailField):
    def to_internal_value(self, data: Any) -> str:
        value: str = super().to_internal_value(data)
        return value.lower()


class RegisterRequestSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField(
        max_length=320,
        validators=[
            UniqueValidator(queryset=User.objects.all(), lookup='iexact')
        ]
    )
    password = PasswordField()
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    isAgreedTerms = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    isAgreedPrivacyPolicy = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    language = LanguageField()


class VerifyEmailRequestSerializer(serializers.Serializer):
    key = serializers.UUIDField()


class LoginRequestSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField()
    password = serializers.CharField()


class ChangePasswordRequestSerializer(serializers.Serializer):
    oldPassword = serializers.CharField(max_length=100)
    newPassword = PasswordField()


class RequestResetPasswordSerializer(serializers.Serializer):
    email = CaseInsensitiveEmailField()


class ActivateResetPasswordSerializer(serializers.Serializer):
    key = serializers.UUIDField()


class ResetPasswordSerializer(serializers.Serializer):
    key = serializers.UUIDField()
    password = PasswordField()


class UserProfileResponseSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source='user.uuid')
    userEmail = serializers.CharField(source='user.email')
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    userName = serializers.CharField(source='username')
    userPhone = serializers.SerializerMethodField(method_name='get_user_phone')
    isEmailConfirmed = serializers.BooleanField(source='user.is_email_confirmed')
    isPhoneConfirmed = serializers.BooleanField(source='is_phone_confirmed')
    isAgreedTerms = serializers.BooleanField(source='is_agreed_terms')
    isAgreedPrivacyPolicy = serializers.BooleanField(source='is_agreed_privacy_policy')
    kycStatus = serializers.ChoiceField(source='kyc_status', choices=Profile.KYC_STATUS_CHOICES)
    language = LanguageField()

    class Meta:
        model = Profile
        fields = (
            'uuid', 'userEmail', 'firstName', 'lastName', 'userName', 'isEmailConfirmed', 'userPhone',
            'isPhoneConfirmed', 'isAgreedTerms', 'isAgreedPrivacyPolicy', 'kycStatus',
            'language'
        )

    def get_user_phone(self, profile: Profile) -> Optional[str]:
        phone = profile.phone
        if phone is None:
            return None
        return phone.number[-4:]


class SetLanguageRequestSerializer(serializers.ModelSerializer):
    language = LanguageField()

    class Meta:
        model = Profile
        fields = (
            'language',
        )
