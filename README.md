# 倉儲作業系統（展示版）

用 Python + Django 寫的倉儲出貨作業系統：匯入電商訂單 Excel 做統計，現場登記出貨數量，再用條碼刷撿貨、配貨，最後在數據塔看每張單走到哪一步。

這是從完整系統整理出來的展示版，只保留基本功能，拿掉職級、部門、工位、到班這些組織管理。

## 功能

| 功能 | 網址 | 說明 |
| --- | --- | --- |
| 登入 | `/accounts/login/` | 用工號登入，不開放註冊，帳號由管理員在後台建立 |
| 訂單統計 | `/orders/` | 一次匯入急單、出貨中、新訂單幾個 Excel，依「統計分組」算出各組訂單數、切單前後張數 |
| 當日統計 | `/daily/` | 當天確定出貨的訂單池，可分好幾批累加匯入，重複的訂單只算一次；可搜尋訂單、抽起或放回 |
| 登記紀錄 | `/records/` | 登記出貨編號、種類、數量；同一種類登記的總數不能超過當日統計的數字 |
| 撿貨登記 | `/worklog/picking/` | 刷編號＋員工編號，第一次刷記開始、同一個人再刷一次記結束；換別人刷是交接，由他接手做完；編號要先在登記紀錄有 |
| 配貨登記 | `/worklog/allocation/` | 同上；編號要先撿貨過，撿貨還沒結束就開始配貨會標記異常（管理員看得到） |
| 數據塔 | `/tower/` | 只有管理員能看：各種類的總數、已登記，以及每個編號目前是未開始、撿貨中、配貨中還是完成 |
| 後台管理 | `/manage/` | 只有管理員能進：系統帳號、匯入欄位對應、統計分組、匯入分類、重複刷間隔 |

## 帳號與權限

- 帳號只有工號、姓名、密碼和「是否為管理員」。工號就是登入帳號，也是撿貨、配貨時刷的員工編號。
- 一般帳號：可以使用數據塔以外的功能頁；登記紀錄、撿貨、配貨只能修改或刪除自己登記的。
- 管理員：另外可以看數據塔、進後台管理、修改刪除別人的紀錄、看配貨異常。

## 安裝與執行

需要 Python 3.11 以上。預設使用 SQLite，不用另外安裝資料庫。

```bash
# 1. 建立並啟用虛擬環境
python -m venv .venv
# Windows：.venv\Scripts\activate
# macOS / Linux：source .venv/bin/activate

# 2. 安裝套件
pip install -r requirements.txt

# 3. 建立資料表
python manage.py migrate

# 4. 建立展示資料：帳號、匯入欄位對應、統計分組、匯入分類
python manage.py seed_demo

# 5. 啟動
python manage.py runserver
```

打開 http://127.0.0.1:8000/ 登入：

| 帳號 | 密碼 | 身分 |
| --- | --- | --- |
| `admin` | `demo1234` | 管理員 |
| `staff01` | `demo1234` | 一般帳號 |

想改用 MySQL：複製 `.env.example` 成 `.env`，設定 `DB_ENGINE=mysql` 和資料庫帳密，先在 MySQL 建好資料庫（`CREATE DATABASE warehouse CHARACTER SET utf8mb4;`）再 `migrate`。

## 讓其他設備臨時連進來（Cloudflare Tunnel）

展示時想讓手機、平板或別人的電腦在任何地方都能開，可以用 Cloudflare Tunnel 產生一個臨時的公開網址，不用註冊帳號。電腦、`runserver` 和 cloudflared 都要一直開著；重開 cloudflared 網址就會換一個。

1. 安裝 cloudflared（Windows）：`winget install --id Cloudflare.cloudflared`，裝完重開終端機
2. 在 `.env` 加上（沒有 `.env` 就先複製 `.env.example`）：
   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
   DJANGO_CSRF_TRUSTED_ORIGINS=https://*.trycloudflare.com
   ```
3. 照平常啟動：`python manage.py runserver`
4. 另開一個終端機：`cloudflared tunnel --url http://localhost:8000`
5. 畫面會印出一個 `https://xxxx.trycloudflare.com` 網址，任何設備打開就能用

網址是公開的，知道的人都能看到登入頁。展示完記得關掉，也記得改掉 `demo1234` 這種預設密碼。

## 展示流程

`demo/` 資料夾有兩份範例訂單 Excel（買家資料都已遮罩）：

1. 用 `admin` 登入，到「當日統計」匯入 `訂單範例-第1批.xlsx`，看各分組的數字卡。
2. 再匯入 `訂單範例-第2批.xlsx`，數字會累加上去。
3. 到「登記紀錄」選一個種類（例如「無包裝」）登記幾筆編號與數量。
4. 到「撿貨登記」刷剛剛登記的編號，員工編號填 `staff01`；同一個人再刷一次就是結束（換成 `admin` 刷就是交接）。
5. 到「配貨登記」刷同一個編號。
6. 打開「數據塔」，看每個種類的進度和每個編號目前的狀態。

「訂單統計」是獨立的計算工具，可以把同一份 Excel 匯入看統計表，不會影響其他功能。

## 執行測試

```bash
python manage.py test
```

## 專案結構

```
config/            Django 設定、網址
apps/
  accounts/        帳號、登入、權限判斷
  backoffice/      後台管理首頁、選單、共用的列表／新增／編輯／刪除頁
  orders/          訂單統計、匯入欄位對應、統計分組、匯入分類；seed_demo 指令
  daily/           當日統計
  records/         登記紀錄
  worklog/         撿貨、配貨登記
  tower/           數據塔
templates/         全站共用版型與元件
static/            全站共用 CSS、JS
demo/              展示用設定（settings.json）與範例 Excel
```

### 資料怎麼串起來

- 訂單 Excel 的欄名不寫死：後台「匯入欄位對應」設定來源欄名對應到系統欄位（訂單號、平台、店鋪、下單時間、出貨類型……）。
- 「統計分組」用平台 × 店鋪 × 出貨類型的條件把訂單分組，可設切單時間分前後。訂單統計和當日統計共用同一套設定，兩者都用版本管理，同時只有一個版本生效。
- 登記紀錄的「種類」就是統計分組的名稱，總數取當日統計對應分組的數字。
- 撿貨比對登記紀錄的編號，配貨比對撿貨的編號；數據塔用編號把三者串起來。
- 撿貨、配貨的每一筆下面記「作業片段」：誰、從幾點做到幾點、這段是交接還是完成。中途換人時就分成好幾段，之後要算個人產能就用這些片段。
