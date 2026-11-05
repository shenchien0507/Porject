from django.test import TestCase
from django.urls import reverse

from .levels import allows, is_admin
from .models import User
from .testing import Level, make_user


class LoginTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_login_with_employee_id(self):
        make_user("E001")
        response = self.client.post(reverse("login"), {"username": "E001", "password": "pw12345!"})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_wrong_password_rejected(self):
        make_user("E001")
        response = self.client.post(reverse("login"), {"username": "E001", "password": "bad"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_login(self):
        make_user("E002", is_active=False)
        self.client.post(reverse("login"), {"username": "E002", "password": "pw12345!"})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        make_user("E001")
        self.client.login(username="E001", password="pw12345!")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))


class RoleTests(TestCase):
    def test_superuser_is_admin(self):
        user = User.objects.create_superuser("root", password="pw12345!", name="root")
        self.assertTrue(user.is_admin)
        self.assertEqual(user.level_display, "管理員")

    def test_label_shows_name_once_when_same_as_employee_no(self):
        self.assertEqual(make_user("002", name="002").label, "002")
        self.assertEqual(make_user("003", name="小明").label, "003 小明")

    def test_only_admin_passes_rules(self):
        self.assertFalse(allows(make_user("E001"), "records-edit-all"))
        self.assertTrue(allows(make_user("A001", Level.ADMIN), "records-edit-all"))
        self.assertFalse(is_admin(make_user("E002", Level.ADMIN, is_active=False)))

    def test_home_lists_features_for_staff(self):
        make_user("E001")
        self.client.login(username="E001", password="pw12345!")
        response = self.client.get(reverse("home"))
        for label in ["訂單統計", "當日統計", "登記紀錄", "撿貨登記", "配貨登記"]:
            self.assertContains(response, label)
        self.assertNotContains(response, "數據塔")  # 數據塔只有管理員能看
        self.assertNotContains(response, "後台管理")


class UserManageTests(TestCase):
    def setUp(self):
        self.admin = make_user("A001", Level.ADMIN)
        self.client.login(username="A001", password="pw12345!")

    def test_staff_cannot_open_backoffice(self):
        make_user("E001")
        self.client.login(username="E001", password="pw12345!")
        self.assertEqual(self.client.get(reverse("backoffice:dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts_manage:user_list")).status_code, 403)

    def test_admin_creates_account_directly(self):
        response = self.client.post(reverse("accounts_manage:user_create"), {
            "username": "E010", "name": "小美", "is_active": "on",
            "password1": "Sx9!pw-long", "password2": "Sx9!pw-long",
        })
        self.assertRedirects(response, reverse("accounts_manage:user_list"))
        user = User.objects.get(username="E010")
        self.assertEqual((user.name, user.is_admin, user.employee_no), ("小美", False, "E010"))
        self.assertTrue(user.check_password("Sx9!pw-long"))

    def test_cannot_remove_own_admin(self):
        self.client.post(reverse("accounts_manage:user_edit", args=[self.admin.pk]), {"name": "新名字", "email": ""})
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.name, self.admin.is_admin, self.admin.is_active), ("新名字", True, True))

    def test_reset_password(self):
        user = make_user("E001")
        self.client.post(reverse("accounts_manage:user_password", args=[user.pk]), {
            "new_password1": "Sx9!pw-long", "new_password2": "Sx9!pw-long",
        })
        user.refresh_from_db()
        self.assertTrue(user.check_password("Sx9!pw-long"))
