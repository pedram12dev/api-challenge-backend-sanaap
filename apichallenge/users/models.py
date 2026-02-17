from django.db import models
from apichallenge.common.models import BaseModel

from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager as BUM
from django.contrib.auth.models import PermissionsMixin


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


class BaseUserManager(BUM):
    def create_user(self, username, is_active=True, is_admin=False, password=None, role=Role.VIEWER):
        if not username:
            raise ValueError("Users must have a username")

        user = self.model(
            username=username.strip(),
            is_active=is_active,
            is_admin=is_admin,
            role=role,
        )

        if password is not None:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()
        user.save(using=self._db)

        return user

    def create_superuser(self, username, password=None):
        user = self.create_user(
            username=username,
            is_active=True,
            is_admin=True,
            password=password,
            role=Role.ADMIN,
        )

        user.is_superuser = True
        user.save(using=self._db)

        return user


class BaseUser(BaseModel, AbstractBaseUser, PermissionsMixin):

    username = models.CharField(max_length=150, unique=True)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    objects = BaseUserManager()

    USERNAME_FIELD = "username"

    def __str__(self):
        return self.username

    @property
    def is_staff(self):
        return self.is_admin
