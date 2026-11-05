"""測試用：建立帳號的捷徑。"""

from .models import User


class Level:
    """make_user(level=Level.ADMIN) 建立管理員；其他值都是一般帳號。"""

    ADMIN = "admin"
    STAFF = "staff"


def make_user(username, level=None, **extra):
    if level == Level.ADMIN:
        extra["is_admin"] = True
    extra.setdefault("name", username)
    return User.objects.create_user(username, password="pw12345!", **extra)
