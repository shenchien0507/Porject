"""選單：新增頁面時，在 MENU 加一筆即可出現在導覽列。
section="backoffice" 的頁面列在後台管理首頁（公司組織、帳號與權限這類設定）；section="feature" 的是獨立功能，在導覽列有自己的入口：
同一個 group 的功能收成一個下拉（只看得到一項時直接顯示連結），group 為 TOOLS_GROUP 的放在右側帳號選單裡。"""

from dataclasses import dataclass

from apps.accounts.levels import is_admin
from apps.accounts.permissions import can_access


TOOLS_GROUP = "工具"


@dataclass(frozen=True)
class MenuItem:
    page_key: str
    label: str
    url_name: str
    group: str
    admin_only: bool = False  # 只有管理員能用；其他頁面登入就能用
    section: str = "backoffice"


MENU = [
    MenuItem("order-stats", "訂單統計", "orders:run_list", "訂單", section="feature"),
    MenuItem("daily-stats", "當日統計", "daily:day_list", "訂單", section="feature"),
    MenuItem("records", "登記紀錄", "records:list", "作業", section="feature"),
    MenuItem("worklog-picking", "撿貨登記", "worklog:picking", "作業", section="feature"),
    MenuItem("worklog-allocation", "配貨登記", "worklog:allocation", "作業", section="feature"),
    MenuItem("data-tower", "數據塔", "tower:index", "數據", admin_only=True, section="feature"),
    # 後台設定只有管理員能用
    MenuItem("manage-users", "系統帳號", "accounts_manage:user_list", "帳號", admin_only=True),
    MenuItem("manage-order-import", "匯入欄位對應", "orders_manage:version_list", "訂單", admin_only=True),
    MenuItem("manage-order-groups", "統計分組", "orders_manage:group_version_list", "訂單", admin_only=True),
    MenuItem("manage-order-categories", "匯入分類", "orders_manage:category_list", "訂單", admin_only=True),
    MenuItem("manage-worklog-setting", "重複刷間隔", "worklog_manage:setting", "撿貨配貨設定", admin_only=True),
]

MENU_BY_KEY = {item.page_key: item for item in MENU}


def can_use(user, item):
    return is_admin(user) if item.admin_only else can_access(user, item.page_key)


def accessible_menu(user, section=None):
    return [item for item in MENU if (section is None or item.section == section) and can_use(user, item)]



def split_features(items):
    """導覽列與首頁用：把能用的獨立功能依 group 分組（保持 MENU 順序），工具另外列出。"""
    groups, tools = {}, []
    for item in items:
        if item.group == TOOLS_GROUP:
            tools.append(item)
        else:
            groups.setdefault(item.group, []).append(item)
    return groups, tools
