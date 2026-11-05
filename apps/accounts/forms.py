from django import forms
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm

from .models import User


class UserCreateForm(UserCreationForm):
    """直接建立帳號：工號（登入帳號、撿貨配貨刷的員工編號）、姓名、密碼。"""

    field_order = ["username", "name", "is_admin", "is_active", "password1", "password2"]

    class Meta:
        model = User
        fields = ["username", "name", "is_admin", "is_active"]

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "工號"
        self.fields["username"].help_text = "登入用的帳號，也是撿貨、配貨登記時刷的員工編號"


class UserUpdateForm(forms.ModelForm):
    """工號不能改；不能取消自己的管理員。"""

    class Meta:
        model = User
        fields = ["username", "name", "email", "is_admin", "is_active"]

    def __init__(self, *args, editor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "工號"
        self.fields["username"].disabled = True
        if self.instance.pk == editor.pk or self.instance.is_superuser:
            self.fields["is_admin"].disabled = True
            self.fields["is_active"].disabled = True


class UserPasswordForm(SetPasswordForm):
    """管理者幫使用者重設密碼，不需要舊密碼。"""
