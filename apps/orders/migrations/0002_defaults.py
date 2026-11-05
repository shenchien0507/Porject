"""預設資料：匯入欄位對應 v1、統計分組 v1（都生效），以及三個匯入分類。
欄位對應 v1 對應電商後台匯出的「歷史紀錄」欄名；統計分組 v1 是最基本的四組。展示用的完整分組由 seed_demo 指令另外建立。"""

import datetime

from django.db import migrations
from django.utils import timezone

SOURCE_COLUMNS = [
    "交易平台", "交易店鋪", "交易序號", "買家姓名", "出貨日期", "出貨類型", "商品編號", "商品名稱", "商品樣式",
    "小計數量", "建立時間", "會員交易筆數", "系統備註", "發票紀錄", "發票開立方式", "收件者姓名", "平台訂單編號",
    "出貨單號", "商品小計", "商品單價", "收件者手機", "收件者地址", "配送狀態", "配送狀態描述", "店家備註",
]
MAPPINGS = {
    "order_no": "交易序號",
    "platform_order_no": "平台訂單編號",
    "platform": "交易平台",
    "shop": "交易店鋪",
    "order_time": "建立時間",
    "ship_time": "出貨日期",
    "ship_type": "出貨類型",
    "shipment_no": "出貨單號",
    "product_code": "商品編號",
    "product_name": "商品名稱",
    "product_spec": "商品樣式",
    "quantity": "小計數量",
}
GROUPS = [
    ("蝦皮無包裝", 10, True, True, {"platforms": ["蝦皮購物"], "ship_types": ["蝦皮無包裝", "蝦皮無包裝[代收]"]}),
    ("蝦皮隔日到貨", 20, True, False, {"platforms": ["蝦皮購物"], "ship_types": ["蝦皮隔日到貨", "蝦皮隔日到貨[代收]"]}),
    ("蝦皮其他", 30, False, False, {"platforms": ["蝦皮購物"]}),
    ("其他平台", 40, True, False, {}),
]
CATEGORIES = ["急單", "出貨中", "新訂單"]


def create(apps, schema_editor):
    MappingVersion = apps.get_model("orders", "MappingVersion")
    ColumnMapping = apps.get_model("orders", "ColumnMapping")
    GroupVersion = apps.get_model("orders", "GroupVersion")
    StatGroup = apps.get_model("orders", "StatGroup")
    StatCondition = apps.get_model("orders", "StatCondition")
    ImportCategory = apps.get_model("orders", "ImportCategory")
    now = timezone.now()

    if not MappingVersion.objects.exists():
        version = MappingVersion.objects.create(
            number=1, source_file_name="歷史紀錄.xlsx", source_columns=SOURCE_COLUMNS,
            note="預設：電商後台歷史紀錄（一列是一個商品，同一個交易序號是同一張訂單）",
            is_active=True, activated_at=now,
        )
        ColumnMapping.objects.bulk_create(
            ColumnMapping(version=version, field=key, source_column=source) for key, source in MAPPINGS.items()
        )

    if not GroupVersion.objects.exists():
        version = GroupVersion.objects.create(
            number=1, note="預設：蝦皮無包裝、蝦皮隔日到貨分 14:00 前後，其他平台分 14:00 前後", is_active=True, activated_at=now,
        )
        for name, order, split, show_rows, condition in GROUPS:
            group = StatGroup.objects.create(
                version=version, name=name, sort_order=order, cutoff=datetime.time(14, 0) if split else None,
                midnight_uses_import_time=split, show_rows=show_rows,
            )
            StatCondition.objects.create(group=group, **condition)

    for i, name in enumerate(CATEGORIES, start=1):
        ImportCategory.objects.get_or_create(name=name, defaults={"sort_order": i * 10})


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]
    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
