from django.test import TestCase
from django.urls import reverse

from apps.accounts.testing import Level, make_user

from .menu import MENU


class BackofficeTestCase(TestCase):
    def login(self, user):
        self.client.login(username=user.username, password="pw12345!")


class AccessTests(BackofficeTestCase):
    def test_admin_sees_every_page(self):
        self.login(make_user("boss", Level.ADMIN))
        self.assertContains(self.client.get(reverse("home")), "後台管理")
        for item in MENU:
            self.assertEqual(self.client.get(reverse(item.url_name)).status_code, 200, item.page_key)

    def test_staff_uses_features_but_not_backoffice(self):
        self.login(make_user("e1"))
        self.assertNotContains(self.client.get(reverse("home")), "後台管理")
        for item in MENU:
            expected = 403 if item.admin_only else 200
            self.assertEqual(self.client.get(reverse(item.url_name)).status_code, expected, item.page_key)

    def test_dashboard_lists_settings_and_marks_current_page(self):
        self.login(make_user("boss", Level.ADMIN))
        dashboard = self.client.get(reverse("backoffice:dashboard"))
        for label in ["系統帳號", "匯入欄位對應", "統計分組", "匯入分類", "重複刷間隔"]:
            self.assertContains(dashboard, label)
        response = self.client.get(reverse("accounts_manage:user_list"))
        self.assertContains(response, f'active" href="{reverse("accounts_manage:user_list")}"')


class WorklogSettingTests(BackofficeTestCase):
    def test_save_rescan_seconds(self):
        from apps.worklog.models import WorklogSetting

        self.login(make_user("boss", Level.ADMIN))
        response = self.client.post(reverse("worklog_manage:setting"), {"rescan_seconds": 30})
        self.assertRedirects(response, reverse("worklog_manage:setting"))
        self.assertEqual(WorklogSetting.load().rescan_seconds, 30)


class NavbarTests(BackofficeTestCase):
    def test_groups_become_dropdowns_and_single_items_plain_links(self):
        self.login(make_user("e1"))
        response = self.client.get(reverse("home"))
        groups = response.context["feature_groups"]
        self.assertEqual(list(groups), ["訂單", "作業"])  # 數據塔只有管理員看得到
        self.assertEqual([item.label for item in groups["作業"]], ["登記紀錄", "撿貨登記", "配貨登記"])
        self.assertContains(response, 'data-bs-toggle="dropdown" aria-expanded="false">作業</a>', html=False)
        self.assertNotContains(response, "數據塔")
        self.assertEqual(response.context["tool_menu"], [])
        self.login(make_user("boss", Level.ADMIN))
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'<a class="nav-link" href="{reverse("tower:index")}">數據塔</a>', html=True)

    def test_group_is_active_on_its_pages(self):
        self.login(make_user("e1"))
        self.assertEqual(self.client.get(reverse("worklog:picking")).context["active_group"], "作業")
        self.assertIsNone(self.client.get(reverse("home")).context["active_group"])
