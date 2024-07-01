import uuid
from datetime import datetime, timedelta
from random import random

from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from rest_framework_simplejwt.tokens import RefreshToken

from base.models import BaseModel

ORDINARY_USER, MANAGER, ADMIN = ("ordinary_user", "manager", "admin")
VIA_EMAIL, VIA_PHONE = ("via_email", "via_phone")
NEW, CODE_VERIFIED, DONE, PHOTO_STEP = ("new", "code_verified", "done", "photo_step")


class User(AbstractUser, BaseModel):
    USER_ROLES = (
        (ORDINARY_USER, ORDINARY_USER),
        (MANAGER, MANAGER),
        (ADMIN, ADMIN),
    )
    AUTH_TYPE_CHOICES = (
        (VIA_EMAIL, VIA_EMAIL),
        (VIA_PHONE, VIA_PHONE),
    )
    AUTH_STATUS_CHOICES = (
        (NEW, NEW),
        (CODE_VERIFIED, CODE_VERIFIED),
        (DONE, DONE),
        (PHOTO_STEP, PHOTO_STEP),
    )
    USER_ROLES = models.CharField(max_length=32, choices=USER_ROLES, default=ORDINARY_USER)
    auth_type = models.CharField(max_length=32, choices=AUTH_TYPE_CHOICES)
    auth_status = models.CharField(max_length=32, choices=AUTH_STATUS_CHOICES, default=NEW)
    email = models.EmailField(null=True, blank=True, unique=True)
    phone_number = models.CharField(max_length=13, null=True, blank=True, unique=True)
    photo = models.ImageField(upload_to='user_photos/', null=True, blank=True,
                              validators=[
                                  FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'heic', 'heif'])])

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def create_verify_code(self, verify_type):
        code = "".join([str(random.randint(0, 10000) % 10) for _ in range(4)])
        UserConfirmation.objects.create(
            user_id=self.id,
            verify_type=verify_type,
            code=code
        )
        return code

    def check_username(self):
        if not self.username:
            temp_username = f'user-{uuid.uuid4().__str__().split("-")[-1]}'
            while User.objects.filter(username=temp_username):
                temp_username = f"{temp_username}{random.randint(0, 9)}"
                self.username = temp_username

    def check_email(self):
        if self.email:
            normalize_email = self.email.lower()  # GGHKawdjK@gmail.com -> gghkawdjk@gmail.com
            self.email = normalize_email

    def check_password(self):
        if not self.password:
            temp_password = f'password-{uuid.uuid4().__str__().split("-")[-1]}'
            self.password = temp_password

    def hashing_password(self):
        if not self.password.startswith('pbkdf2_sha256'):
            self.set_password(self.password)

    def token(self):
        refresh = RefreshToken.for_user(self)
        return {
            "access": str(refresh.access_token),
            "refresh_token": str(refresh),
        }

    def save(self, *args, **kwargs):
        self.clean()
        super(User, self).save(*args, **kwargs)

        # save -> database

    def clean(self):
        self.check_email()
        self.check_username()
        self.check_password()
        self.hashing_password()


PHONE_EXPIRE = 3
EMAIL_EXPIRE = 6


class UserConfirmation(BaseModel):
    TYPE_CHOICES = (
        (VIA_EMAIL, VIA_EMAIL),
        (VIA_PHONE, VIA_PHONE),
    )
    code = models.CharField(max_length=4)
    verify_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    user = models.ForeignKey('users.User', models.CASCADE, related_name='verify_codes')
    expiration_time = models.DateField(null=True)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user.__str__())

    def save(self, *args, **kwargs):
        # if not self.pk:
        if self.verify_type == VIA_EMAIL:
            self.expiration_time = datetime.now() + timedelta(minutes=EMAIL_EXPIRE)
        else:
            self.expiration_time = datetime.now() + timedelta(minutes=PHONE_EXPIRE)
        super(UserConfirmation, self).save(*args, **kwargs)

