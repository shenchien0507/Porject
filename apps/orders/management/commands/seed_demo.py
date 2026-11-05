"""展示用的初始資料：python manage.py seed_demo

建立兩個帳號（管理員 admin、一般帳號 staff01，密碼都是 demo1234），以及展示用的統計分組（26 組）並設為生效。
匯入欄位對應 v1、匯入分類在 migrate 時就建立了（orders/migrations/0002_defaults.py）。
分組內容放在 demo/settings.json。重複執行不會重複建立。"""

import json
from datetime import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import GroupVersion, StatCondition, StatGroup

SETTINGS_FILE = settings.BASE_DIR / "demo" / "settings.json"
PASSWORD = "demo1234"
NOTE = "展示用分組（seed_demo 建立）"
ACCOUNTS = [
    ("admin", "管理員", True),
    ("staff01", "示範員工", False),
]


class Command(BaseCommand):
    help = "建立展示用的帳號與統計分組"

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        self.accounts()
        self.groups(data)
        self.stdout.write(self.style.SUCCESS("完成。用 admin / demo1234（管理員）或 staff01 / demo1234（一般帳號）登入。"))

    def accounts(self):
        for username, name, is_admin in ACCOUNTS:
            if User.objects.filter(username=username).exists():
                self.stdout.write(f"帳號 {username} 已存在，略過")
                continue
            User.objects.create_user(username, password=PASSWORD, name=name, is_admin=is_admin)
            self.stdout.write(f"建立帳號 {username}（{name}）")

    def groups(self, data):
        if GroupVersion.objects.filter(note=NOTE).exists():
            self.stdout.write("已經有展示用統計分組，略過")
            return
        GroupVersion.objects.update(is_active=False)
        number = (GroupVersion.objects.order_by("-number").values_list("number", flat=True).first() or 0) + 1
        version = GroupVersion.objects.create(
            number=number, note=NOTE, source_file_name=data["source_file_name"],
            source_combos=data["source_combos"], is_active=True, activated_at=timezone.now(),
        )
        for item in data["items"]:
            item = dict(item)
            conditions = item.pop("conditions")
            if item["cutoff"]:
                item["cutoff"] = time.fromisoformat(item["cutoff"])
            group = StatGroup.objects.create(version=version, **item)
            StatCondition.objects.bulk_create(StatCondition(group=group, **condition) for condition in conditions)
        self.stdout.write(f"建立統計分組 v{number}（{len(data['items'])} 組）並設為生效")
