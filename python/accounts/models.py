from random import randint
import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import RegexValidator

from .utils import send_sms


class MyUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Użytkownicy muszą mieć adres email'))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_phone_verified', True)
        return self.create_user(email, username, password, **extra_fields)

class MyUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name=_('Email'))
    username = models.CharField(max_length=255, unique=True, verbose_name=_('Nazwa użytkownika'))
    is_active = models.BooleanField(default=True, verbose_name=_('Aktywny'))
    is_staff = models.BooleanField(default=False, verbose_name=_('Członek personelu'))
    is_verified = models.BooleanField(default=False, verbose_name=_('Zweryfikowany'))
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    email_verification_expiry = models.DateTimeField(default=timezone.now, null=True, blank=True)
    phone_number = models.CharField(validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],  max_length=17, blank=True, verbose_name=_('Phone Number'))
    phone_verification_code = models.CharField(max_length=6, null=True, blank=True, verbose_name=_('Phone Verification Code'))
    is_phone_verified = models.BooleanField(default=False, verbose_name=_('Phone Verified'))
    password_reset_required = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _('Użytkownik')
        verbose_name_plural = _('Użytkownicy')
        ordering = ['id']

    def send_phone_verification_code(self):
        verification_code = '{:06d}'.format(randint(0, 999999))
        self.phone_verification_code = verification_code
        self.save()

        message_body = f"Your verification code is {verification_code}"
        send_sms(self.phone_number, message_body)


class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expiry
