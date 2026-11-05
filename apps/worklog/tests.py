from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.testing import Level, make_user
from apps.records.models import Record

from .models import Stage, WorkEntry, WorklogSetting, WorkSegment

PICK, ALLOC = "/worklog/picking/", "/worklog/allocation/"


class WorklogTests(TestCase):
    def setUp(self):
        self.picker = make_user("P001", Level.STAFF)
        self.allocator = make_user("A001", Level.STAFF)
        self.director = make_user("D001", Level.ADMIN)
        self.e1 = make_user("E001", name="小明")
        self.e2 = make_user("E002", name="小華")
        Record.objects.create(number="N001", name="紙箱", quantity=1)
        WorklogSetting.objects.create(pk=1, rescan_seconds=0)  # 這組測試連續刷，不限制間隔（RescanTests 另外測）
        self.login(self.picker)

    def login(self, user):
        self.client.login(username=user.username, password="pw12345!")

    def scan(self, url, number, employee_no="E001"):
        return self.client.post(url, {"number": number, "employee_no": employee_no})

    def test_urls(self):
        self.assertEqual(reverse("worklog:picking"), PICK)
        self.assertEqual(reverse("worklog:allocation"), ALLOC)


    def test_first_scan_starts_second_ends_third_is_blocked(self):
        self.assertRedirects(self.scan(PICK, "N001"), PICK)
        entry = WorkEntry.objects.get()
        self.assertEqual((entry.stage, entry.start_employee, entry.ended_at, entry.created_by), (Stage.PICKING, self.e1, None, self.picker))

        self.scan(PICK, "N001")
        entry.refresh_from_db()
        self.assertEqual(entry.end_employee, self.e1)
        self.assertIsNotNone(entry.ended_at)
        segment = entry.segments.get()
        self.assertEqual((segment.employee, segment.outcome), (self.e1, WorkSegment.DONE))

        self.assertContains(self.scan(PICK, "N001"), "撿貨已經結束，下一步是配貨")  # 每個階段只走一輪
        self.assertEqual(WorkEntry.objects.count(), 1)

    def test_other_employee_scanning_takes_over(self):
        self.scan(PICK, "N001", "E001")
        response = self.client.post(PICK, {"number": "N001", "employee_no": "E002"}, follow=True)
        self.assertContains(response, "N001 由 E002 小華 接手（原本是 E001 小明")
        entry = WorkEntry.objects.get()
        self.assertTrue(entry.is_open)  # 交接不算結束
        self.assertEqual((entry.start_employee, entry.current_employee), (self.e1, self.e2))
        self.assertContains(response, "交接：E001 小明 →")
        self.assertContains(response, "目前：E002 小華")

        self.scan(PICK, "N001", "E002")  # 接手的人再刷一次才完成
        entry.refresh_from_db()
        self.assertEqual((entry.start_employee, entry.end_employee), (self.e1, self.e2))
        self.assertFalse(entry.is_open)
        self.assertEqual(
            [(s.employee, s.outcome, s.ended_at is not None) for s in entry.segment_list],
            [(self.e1, WorkSegment.HANDOVER, True), (self.e2, WorkSegment.DONE, True)],
        )
        self.assertEqual(entry.segment_list[0].ended_at, entry.segment_list[1].started_at)

    def test_handover_back_and_forth(self):
        self.scan(PICK, "N001", "E001")
        self.scan(PICK, "N001", "E002")
        self.scan(PICK, "N001", "E001")  # 又換回 E001：再交接一次
        entry = WorkEntry.objects.get()
        self.assertTrue(entry.is_open)
        self.assertEqual([s.employee for s in entry.segment_list], [self.e1, self.e2, self.e1])
        self.scan(PICK, "N001", "E001")
        entry.refresh_from_db()
        self.assertEqual(entry.end_employee, self.e1)

    def test_editing_employees_updates_first_and_last_segment(self):
        self.scan(PICK, "N001", "E001")
        self.scan(PICK, "N001", "E002")
        self.scan(PICK, "N001", "E002")
        entry = WorkEntry.objects.get()
        e3 = make_user("E003", name="小美")
        self.client.post(reverse("worklog:picking_edit", args=[entry.pk]), {
            "number": "N001", "start_employee_no": "E003", "end_employee_no": "E003",
        })
        self.assertEqual([s.employee for s in WorkEntry.objects.get().segment_list], [e3, e3])

    def test_each_number_goes_through_one_cycle(self):
        self.scan(PICK, "N001")
        self.scan(PICK, "N001")
        self.scan(ALLOC, "N001")
        self.assertContains(self.scan(PICK, "N001"), "已經進到配貨，不能再撿貨")
        self.scan(ALLOC, "N001")
        self.assertContains(self.scan(ALLOC, "N001"), "配貨已經完成")
        self.assertEqual(WorkEntry.objects.count(), 2)
        # 要重做：刪掉舊的登記就能再走一輪
        WorkEntry.objects.all().delete()
        self.scan(PICK, "N001")
        self.assertTrue(WorkEntry.objects.get().is_open)

    def test_picking_number_must_be_in_records(self):
        response = self.scan(PICK, "X999")
        self.assertContains(response, "登記紀錄沒有編號「X999」")
        self.assertFalse(WorkEntry.objects.exists())

    def test_employee_must_be_active_account(self):
        make_user("E009", name="離職", is_active=False)
        for employee_no in ["E404", "E009"]:
            self.assertContains(self.scan(PICK, "N001", employee_no), "系統帳號沒有啟用中的工號")
        self.assertFalse(WorkEntry.objects.exists())

    def test_allocation_number_must_be_in_picking(self):
        self.login(self.allocator)
        self.assertContains(self.scan(ALLOC, "N001"), "撿貨沒有編號「N001」")
        self.scan(PICK, "N001")
        self.assertRedirects(self.scan(ALLOC, "N001"), ALLOC)
        self.assertEqual(WorkEntry.objects.filter(stage=Stage.ALLOCATION).count(), 1)

    def test_allocation_before_picking_ends_is_anomaly_seen_by_director_only(self):
        self.scan(PICK, "N001")
        self.scan(ALLOC, "N001")
        entry = WorkEntry.objects.get(stage=Stage.ALLOCATION)
        self.assertTrue(entry.anomaly)
        self.assertNotContains(self.client.get(ALLOC), "撿貨未結束")
        self.login(self.director)
        self.assertContains(self.client.get(ALLOC), "撿貨未結束")
        self.assertContains(self.client.get(ALLOC + "?anomaly=1"), "N001")

    def test_allocation_after_picking_ends_is_normal(self):
        self.scan(PICK, "N001")
        self.scan(PICK, "N001")
        self.scan(ALLOC, "N001")
        self.assertFalse(WorkEntry.objects.get(stage=Stage.ALLOCATION).anomaly)

    def test_pages_list_only_their_own_stage(self):
        Record.objects.create(number="N002", name="膠帶", quantity=1)
        self.scan(PICK, "N001")
        self.scan(PICK, "N001")
        self.scan(ALLOC, "N001")
        self.scan(PICK, "N002")
        self.assertContains(self.client.get(ALLOC), "N001")
        self.assertNotContains(self.client.get(ALLOC), "N002")

    def test_edit_numbers_and_employees_but_not_times(self):
        self.scan(PICK, "N001")
        self.scan(PICK, "N001")
        entry = WorkEntry.objects.get()
        started, ended = entry.started_at, entry.ended_at
        Record.objects.create(number="N002", name="膠帶", quantity=1)
        url = reverse("worklog:picking_edit", args=[entry.pk])
        data = {"number": "N002", "start_employee_no": "E002", "end_employee_no": "E002", "started_at": "2000-01-01 00:00"}
        self.assertRedirects(self.client.post(url, data), PICK)
        entry.refresh_from_db()
        self.assertEqual((entry.number, entry.start_employee, entry.end_employee, entry.updated_by), ("N002", self.e2, self.e2, self.picker))
        self.assertEqual((entry.started_at, entry.ended_at), (started, ended))
        self.assertContains(self.client.post(url, {**data, "number": "X999"}), "登記紀錄沒有編號")

    def test_only_own_account_or_director_can_edit_and_delete(self):
        self.scan(PICK, "N001")
        entry = WorkEntry.objects.get()
        self.login(self.allocator)
        self.assertEqual(self.client.get(reverse("worklog:picking_edit", args=[entry.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("worklog:picking_delete", args=[entry.pk])).status_code, 403)
        self.login(self.director)
        self.assertEqual(self.client.get(reverse("worklog:picking_edit", args=[entry.pk])).status_code, 200)
        self.client.post(reverse("worklog:picking_delete", args=[entry.pk]))
        self.assertFalse(WorkEntry.objects.exists())

    def test_entry_of_other_stage_is_not_reachable(self):
        self.scan(PICK, "N001")
        entry = WorkEntry.objects.get()
        self.assertEqual(self.client.get(reverse("worklog:allocation_edit", args=[entry.pk])).status_code, 404)


class RescanTests(TestCase):
    """同一個編號刷完後，設定的秒數內再刷擋下（條碼槍連刷、Enter 按兩次）。"""

    def setUp(self):
        make_user("E001", name="小明")
        Record.objects.create(number="N001", name="紙箱", quantity=1)
        self.client.login(username=make_user("P001", Level.STAFF).username, password="pw12345!")

    def scan(self, seconds_later=0):
        now = timezone.now() + timedelta(seconds=seconds_later)
        with mock.patch("django.utils.timezone.now", return_value=now):
            return self.client.post(PICK, {"number": "N001", "employee_no": "E001"}, follow=True)

    def test_second_scan_within_seconds_is_blocked(self):
        WorklogSetting.objects.create(pk=1, rescan_seconds=10)
        self.scan()
        self.assertContains(self.scan(3), "秒內再刷不算")
        self.assertTrue(WorkEntry.objects.get().is_open)
        self.scan(11)
        self.assertFalse(WorkEntry.objects.get().is_open)
        self.assertContains(self.scan(14), "秒內再刷不算")  # 剛結束也一樣
        self.assertEqual(WorkEntry.objects.count(), 1)

    def test_zero_means_no_limit(self):
        WorklogSetting.objects.create(pk=1, rescan_seconds=0)
        self.scan()
        self.scan()
        self.assertFalse(WorkEntry.objects.get().is_open)

    def test_setting_page(self):
        self.client.login(username=make_user("root", Level.ADMIN).username, password="pw12345!")
        url = reverse("worklog_manage:setting")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {"rescan_seconds": 5})
        self.assertEqual(WorklogSetting.load().rescan_seconds, 5)
