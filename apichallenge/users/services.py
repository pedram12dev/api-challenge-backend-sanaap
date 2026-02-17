from .models import BaseUser, Role


def create_user(*, username: str, password: str, role: str = Role.VIEWER) -> BaseUser:
    return BaseUser.objects.create_user(username=username, password=password, role=role)


def register(*, username: str, password: str) -> BaseUser:
    return create_user(username=username, password=password)
