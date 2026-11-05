from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """username 即工號，撿貨、配貨登記時刷的員工編號也是它。離職請停用（is_active=False），不要刪除。
    這個展示版沒有職級、部門：一般帳號可以用所有功能，管理員另外可以進後台、修改刪除別人的紀錄。"""

    first_name = None
    last_name = None

    name = models.CharField("姓名", max_length=50)
    is_admin = models.BooleanField("管理員", default=False, help_text="管理員可以進後台管理，也可以修改、刪除別人登記的紀錄")

    class Meta:
        verbose_name = "使用者"
        verbose_name_plural = "使用者"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.is_admin = True
        super().save(*args, **kwargs)

    @property
    def level_display(self):
        return "管理員" if self.is_admin else "一般帳號"

    @property
    def employee_no(self):
        """撿貨、配貨刷的員工編號就是工號。"""
        return self.username

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name or self.username

    def __str__(self):
        return f"{self.username} {self.name}".strip()
