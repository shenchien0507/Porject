"""權限判斷。展示版沒有職級：管理員可以做所有事，一般帳號只能動自己登記的資料。"""


def is_admin(user):
    return bool(user.is_authenticated and user.is_active and (user.is_admin or user.is_superuser))


def allows(user, code):
    """原本依職級門檻判斷的操作（例如修改別人的紀錄、看配貨異常），展示版一律只開放給管理員。
    code 保留下來，之後要細分權限時可以從這裡開始。"""
    return is_admin(user)
