"""頁面權限：展示版沒有頁面權限設定，登入且啟用中的帳號都能使用功能頁。"""


def can_access(user, page_key):
    return bool(user.is_authenticated and user.is_active)
