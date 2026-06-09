# 📋 HƯỚNG DẪN THỰC HÀNH CHI TIẾT — PHẦN 3.4: THỰC NGHIỆM CHẠY HỆ THỐNG GỐC

> **Mục đích**: Tài liệu này hướng dẫn bạn thực hiện từng bước một phần 3.4 trong
> báo cáo, bao gồm: khởi động hệ thống, kích hoạt tác vụ, quan sát kết quả,
> và chụp toàn bộ ảnh minh họa cần thiết cho báo cáo bài tập lớn.

---

## 📐 SƠ ĐỒ TỔNG QUAN: BẠN SẼ MỞ BAO NHIÊU CỬA SỔ?

Toàn bộ quá trình demo cần **4 Terminal** + **2 Tab trình duyệt** chạy đồng thời:

```
┌──────────────────────────────────────────────────────────────────────┐
│                      MÁY TÍNH CỦA BẠN                                │
│                                                                      │
│  ┌─── Terminal 0 ───┐   (Bước 1) docker compose up -d                │
│  │  Docker Desktop  │   → Khởi động RabbitMQ + Redis + PostgreSQL    │
│  └──────────────────┘                                                │
│                                                                      │
│  ┌─── Terminal 1 ───┐   (Bước 2) celery worker                       │
│  │  Celery Worker   │   → Luôn mở, hiển thị log xử lý task realtime  │
│  └──────────────────┘                                                │
│                                                                      │
│  ┌─── Terminal 2 ───┐   (Bước 3) celery flower                       │
│  │  Flower Monitor  │   → Luôn mở, phục vụ dashboard giám sát        │
│  └──────────────────┘                                                │
│                                                                      │
│  ┌─── Terminal 3 ───┐   (Bước 4) python script                       │
│  │  Client/Producer │   → Nơi bạn gửi task và chạy thực nghiệm       │
│  └──────────────────┘                                                │
│                                                                      │
│  ┌─── Trình duyệt ────────────────────────────────────── ┐            │
│  │  Tab 1: http://localhost:15672  → RabbitMQ Dashboard  │           │
│  │  Tab 2: http://localhost:5555   → Flower Dashboard    │           │
│  └───────────────────────────────────────────────────────┘           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 BƯỚC 0: KIỂM TRA TIỀN ĐIỀU KIỆN

Trước khi bắt đầu, hãy kiểm tra:

| # | Kiểm tra | Cách xác nhận |
|---|----------|---------------|
| 1 | Docker Desktop đang chạy | Mở ứng dụng Docker Desktop trên thanh taskbar, biểu tượng cá voi xanh hiện trạng thái "Engine Running" |
| 2 | Đã clone và cd vào thư mục project | Mở PowerShell, `cd "e:\2026 Year\Kì 3 Năm 3\Ung_Dung_Phan_Tan\Project\celery-project"` |
| 3 | Virtual environment đã tạo | Kiểm tra thư mục `venv/` tồn tại trong project |

---

## 🚀 BƯỚC 1: Khởi động hạ tầng Docker (Terminal 0)

### 1.1 Mở Terminal đầu tiên (PowerShell) và chạy:
```powershell
cd "e:\2026 Year\Kì 3 Năm 3\Ung_Dung_Phan_Tan\Project\celery-project"
docker compose up -d
```

### 1.2 Giải thích chi tiết lệnh:
- `docker compose up`: Đọc file `docker-compose.yml` trong thư mục hiện tại, tải image từ Docker Hub (nếu chưa có) và khởi tạo container.
- `-d` (detach): Chạy ở chế độ nền, không chiếm terminal.
- **Kết quả thành công**: Bạn sẽ thấy 3 dòng trạng thái "Started":
  ```
  ✅ Container celery_rabbitmq  Started
  ✅ Container celery_redis     Started
  ✅ Container celery_postgres  Started
  ```

### 1.3 Kiểm tra container đã chạy:
```powershell
docker ps
```
Kết quả phải hiển thị 3 container ở trạng thái `Up` và `(healthy)`.

### 1.4 Xác nhận kết nối:
- **RabbitMQ**: Mở trình duyệt → `http://localhost:15672`
  - Đăng nhập: `admin` / `admin123`
  - Nếu thấy trang dashboard RabbitMQ → ✅ Thành công
- **Redis**: Chạy lệnh kiểm tra trong PowerShell:
  ```powershell
  docker exec celery_redis redis-cli ping
  ```
  - Kết quả trả về `PONG` → ✅ Redis hoạt động

### 📸 Ảnh chụp nên lấy:
- Ảnh terminal hiển thị `docker ps` với 3 container chạy healthy
- Ảnh giao diện đăng nhập RabbitMQ Dashboard tại `localhost:15672`

---

## 🔧 BƯỚC 2: Khởi động Celery Worker (Terminal 1 — GIỮ MỞ SUỐT BUỔI DEMO)

### 2.1 Mở Terminal MỚI (Terminal 1) và chạy:
```powershell
cd "e:\2026 Year\Kì 3 Năm 3\Ung_Dung_Phan_Tan\Project\celery-project"
.\venv\Scripts\celery.exe -A core.main worker --loglevel=info --pool=solo -n worker1@%h
```

### 2.2 Giải thích chi tiết TỪNG tham số:
| Tham số | Ý nghĩa |
|---------|---------|
| `celery` | Gọi chương trình Celery CLI (Command-Line Interface) |
| `-A core.main` | Chỉ định Celery app nằm ở file `core/main.py` (biến `app = Celery(...)`) |
| `worker` | Lệnh con "worker" — khởi động một Worker Process |
| `--loglevel=info` | Mức độ hiển thị log: `info` hiện vừa đủ thông tin (DEBUG quá chi tiết, WARNING quá ít) |
| `--pool=solo` | Chế độ xử lý: `solo` = xử lý 1 task tại 1 thời điểm (tuần tự). Dùng cho Windows để tránh lỗi PermissionError của pool `prefork` |
| `-n worker1@%h` | Đặt tên cho Worker: `worker1` tại máy `%h` (tên máy tính của bạn, VD: `worker1@hdungx079`) |

### 2.3 Kết quả thành công — Bạn sẽ thấy log kiểu này:
```
 -------------- worker1@hdungx079 v5.6.3 (recovery)
--- ***** -----
-- ******* ---- Windows-11-10.0.26200-SP0

- ** ---------- [config]
- ** ---------- .> app:         celery_project:0x209816fe7b0
- ** ---------- .> transport:   amqp://admin:**@localhost:5672//       ← Kết nối RabbitMQ
- ** ---------- .> results:     redis://localhost:6379/0               ← Kết nối Redis
- *** --- * --- .> concurrency: 8 (solo)                               ← Chế độ solo
-- ******* ---- .> task events: OFF

 -------------- [queues]
                .> default          exchange=default(direct) key=default
                .> high_priority    exchange=high_priority(direct) key=high_priority
                .> low_priority     exchange=low_priority(direct) key=low_priority

[tasks]
  . core.tasks.generate_report_task     ← 3 task đã đăng ký thành công
  . core.tasks.process_image_task
  . core.tasks.send_email_task

[... INFO/MainProcess] worker1@hdungx079 ready.    ← WORKER SẴN SÀNG
```

### 2.4 Cách đọc hiểu log Worker — 4 khối thông tin quan trọng:

**Khối 1 — [config]**: Cấu hình vận hành
- `transport`: Giao thức kết nối tới Message Broker. Ở đây là `amqp://` (giao thức AMQP của RabbitMQ), user `admin`, mật khẩu ẩn `**`, server `localhost:5672`.
- `results`: Nơi lưu kết quả task. Ở đây là Redis tại `localhost:6379`, database số `0`.
- `concurrency`: Số task tối đa có thể xử lý đồng thời. `solo` = 1 task/lần.

**Khối 2 — [queues]**: Các hàng đợi mà Worker này lắng nghe
- `default`: Hàng đợi mặc định cho mọi task.
- `high_priority` / `low_priority`: Hàng đợi ưu tiên (đã được định nghĩa trong `celeryconfig.py`).

**Khối 3 — [tasks]**: Danh sách các hàm Python đã được đăng ký dưới dạng Celery task
- Celery quét (autodiscover) module `core.tasks` và tìm thấy 3 hàm có decorator `@shared_task`.

**Khối 4 — "ready."**: Xác nhận Worker đã kết nối thành công tới Broker và bắt đầu lắng nghe tin nhắn từ các hàng đợi.

### 📸 Ảnh chụp cần lấy (cho mục 3.4.1 báo cáo):
Chụp TOÀN BỘ terminal từ lúc chạy lệnh đến khi thấy dòng `worker1@... ready.`
Dùng bút đỏ khoanh vùng 4 khối thông tin quan trọng nêu trên.

---

## 📊 BƯỚC 3: Khởi động Flower Dashboard (Terminal 2 — GIỮ MỞ SUỐT BUỔI DEMO)

### 3.1 Mở Terminal MỚI (Terminal 2) và chạy:
```powershell
cd "e:\2026 Year\Kì 3 Năm 3\Ung_Dung_Phan_Tan\Project\celery-project"
.\venv\Scripts\celery.exe -A core.main flower --port=5555
```

### 3.2 Giải thích:
- `flower`: Lệnh con khởi động Celery Flower — một ứng dụng web giám sát Celery Worker được viết bằng Tornado.
- `--port=5555`: Mở giao diện web tại cổng 5555.

### 3.3 Mở trình duyệt → `http://localhost:5555`
Bạn sẽ thấy dashboard hiển thị:
- Tab **Dashboard/Workers**: Hiển thị `worker1@hdungx079` với trạng thái **Online** (nhãn xanh lá).
- Các cột: Active (đang xử lý), Processed (đã hoàn thành), Failed (lỗi), Succeeded (thành công).

### 📸 Ảnh chụp: Flower Dashboard khi Worker vừa khởi động (tất cả số liệu = 0, trạng thái Online).

---

## 🎬 BƯỚC 4: KÍCH HOẠT TÁC VỤ BẤT ĐỒNG BỘ TỪ CLIENT (Terminal 3)

Đây là bước quan trọng nhất — mục **3.4.2** trong báo cáo.

### 4.1 Mở Terminal MỚI (Terminal 3) và chạy:
```powershell
cd "e:\2026 Year\Kì 3 Năm 3\Ung_Dung_Phan_Tan\Project\celery-project"
$env:PYTHONIOENCODING="utf-8"
```

### 4.2 Gửi lần lượt 3 loại task vào hàng đợi:

#### 📧 Task 1: Gửi Email
```powershell
.\venv\Scripts\python.exe -c "
from core.tasks import send_email_task
result = send_email_task.delay('user@gmail.com', 'Xin chao', 'Noi dung email test')
print('Task ID:', result.id)
print('Trang thai:', result.status)
"
```

**Kết quả mong đợi:**
```
Task ID: 5ce1c470-a6d3-4f55-8f83-8a6a89aee818
Trang thai: PENDING
```

**Giải thích từng dòng code:**
- `from core.tasks import send_email_task`: Import hàm task đã được đăng ký trong Celery.
- `send_email_task.delay(...)`: Phương thức `.delay()` là cách nhanh nhất để gọi task bất đồng bộ. Nó thực hiện:
  1. Chuyển đổi tham số (`'user@gmail.com'`, `'Xin chao'`, `'Noi dung...'`) thành JSON.
  2. Tạo một UUID duy nhất (`task_id`) cho tin nhắn.
  3. Đẩy tin nhắn JSON vào hàng đợi `default` trên RabbitMQ qua giao thức AMQP.
  4. Trả về ngay lập tức một đối tượng `AsyncResult` chứa `task_id`.
- `result.status` = `PENDING`: Nghĩa là "tin nhắn đã nằm trong hàng đợi, đang chờ Worker kéo về xử lý".

**👀 Lúc này, QUAY SANG TERMINAL 1 (Worker)**, bạn sẽ thấy log mới xuất hiện:
```
[INFO/MainProcess] Task core.tasks.send_email_task[5ce1c470...] received
[INFO/MainProcess] [EMAIL] Đang gửi tới user@gmail.com...
[INFO/MainProcess] [EMAIL] ✅ Gửi thành công tới user@gmail.com (2.34s)
[INFO/MainProcess] Task core.tasks.send_email_task[5ce1c470...] succeeded in 2.34s
```

#### 🖼️ Task 2: Xử lý Ảnh
```powershell
.\venv\Scripts\python.exe -c "
from core.tasks import process_image_task
result = process_image_task.delay('photo_banner.jpg', 1920, 1080)
print('Task ID:', result.id)
print('Trang thai:', result.status)
"
```

#### 📊 Task 3: Tạo Báo Cáo
```powershell
.\venv\Scripts\python.exe -c "
from core.tasks import generate_report_task
result = generate_report_task.delay('sales', '2026-01-01', '2026-06-03')
print('Task ID:', result.id)
print('Trang thai:', result.status)
"
```

### 4.3 Truy vấn kết quả task đã hoàn thành:
Sau khi gửi task, đợi vài giây rồi kiểm tra kết quả bằng `task_id`:
```powershell
.\venv\Scripts\python.exe -c "
from core.main import app
from celery.result import AsyncResult

# Thay task_id bằng ID bạn nhận được ở bước trên
task_id = 'THAY_TASK_ID_CUA_BAN_VAO_DAY'
result = AsyncResult(task_id, app=app)

print('Task ID   :', task_id)
print('Trang thai:', result.status)
print('Ket qua   :', result.result)
"
```

**Kết quả mong đợi:**
```
Trang thai: SUCCESS
Ket qua   : {'status': 'sent', 'recipient': 'user@gmail.com', ...}
```

**Giải thích cơ chế truy vấn:**
- `AsyncResult(task_id, app=app)`: Tạo một "tấm vé hẹn" trỏ tới kết quả lưu trong Redis.
- `result.status`: Truy vấn Redis bằng key `celery-task-meta-{task_id}` để lấy trạng thái.
- `result.result`: Lấy giá trị JSON mà Worker đã ghi vào Redis sau khi xử lý xong.

### 📸 Ảnh chụp cần lấy (cho mục 3.4.2 báo cáo):
1. Ảnh Terminal 3: Hiển thị lệnh gửi 3 task + kết quả PENDING
2. Ảnh Terminal 1 (Worker): Hiển thị log nhận và xử lý 3 task liên tiếp
3. Ảnh Terminal 3: Hiển thị kết quả truy vấn AsyncResult trả về SUCCESS

---

## 📊 BƯỚC 5: QUAN SÁT KẾT QUẢ PHÂN TÁN (Mục 3.4.3 trong báo cáo)

### 5.1 Quan sát trên RabbitMQ Dashboard

Mở trình duyệt → `http://localhost:15672` → Đăng nhập `admin` / `admin123`

**Tab "Overview":**
- Nhìn biểu đồ **Message rates**: Bạn sẽ thấy đường biểu đồ nhảy lên ở 2 chỉ số:
  - `Publish/s` (Tốc độ Producer đẩy tin nhắn vào) — tương ứng thời điểm bạn gọi `.delay()`
  - `Deliver/Ack/s` (Tốc độ Worker kéo tin nhắn ra và xác nhận xong) — tương ứng thời điểm Worker hoàn thành task

**Tab "Queues and Streams":**
- Bạn sẽ thấy 3 hàng đợi đã được tạo: `default`, `high_priority`, `low_priority`.
- Cột **Ready**: Số tin nhắn đang chờ trong hàng đợi (nếu Worker đang xử lý, số này sẽ > 0 rồi giảm về 0).
- Cột **Total**: Tổng số tin nhắn đã từng đi qua hàng đợi.

### 📸 Ảnh chụp cần lấy:
- Ảnh tab Overview có biểu đồ Message rates nhảy
- Ảnh tab Queues hiển thị danh sách 3 queue

### 5.2 Quan sát trên Flower Dashboard

Mở trình duyệt → `http://localhost:5555`

**Tab "Workers":**
- `worker1@hdungx079` — Status: **Online** (xanh lá)
- Cột **Processed**: Số task đã xử lý (ví dụ: 3)
- Cột **Succeeded**: Số task thành công (ví dụ: 3)
- Cột **Failed**: 0

**Tab "Tasks":**
- Hiển thị danh sách chi tiết từng task:
  | Name | UUID | State | Received | Started | Runtime | Worker |
  |------|------|-------|----------|---------|---------|--------|
  | core.tasks.send_email_task | 5ce1c... | SUCCESS | 13:25:01 | 13:25:01 | 2.34s | worker1@hdungx079 |
  | core.tasks.process_image_task | a3b2f... | SUCCESS | 13:25:05 | 13:25:05 | 3.21s | worker1@hdungx079 |
  | core.tasks.generate_report_task | 7d8e1... | SUCCESS | 13:25:10 | 13:25:10 | 4.56s | worker1@hdungx079 |

### ⚠️ LƯU Ý QUAN TRỌNG:
Nếu tab "Tasks" trên Flower không hiển thị danh sách task, bạn cần bật Task Events bằng cách:
- Tắt Worker hiện tại (`Ctrl + C` ở Terminal 1)
- Chạy lại Worker với flag `-E`:
```powershell
.\venv\Scripts\celery.exe -A core.main worker --loglevel=info --pool=solo -n worker1@%h -E
```
Flag `-E` (enable events) ra lệnh cho Worker gửi thông báo sự kiện (event) tới Flower mỗi khi nhận, bắt đầu, hoàn thành một task.

### 📸 Ảnh chụp cần lấy:
- Tab Workers: Hiển thị worker Online, cột Processed/Succeeded có số
- Tab Tasks: Hiển thị danh sách 3 task với trạng thái SUCCESS màu xanh

---

## 🎯 BƯỚC 6 (BONUS): GỬI HÀNG LOẠT TASK ĐỂ CÓ BIỂU ĐỒ ĐẸP HƠN CHO BÁO CÁO

Để Flower và RabbitMQ Dashboard hiển thị biểu đồ throughput nhảy rõ ràng hơn, hãy gửi một loạt task cùng lúc:

```powershell
.\venv\Scripts\python.exe -c "
from core.tasks import send_email_task, process_image_task, generate_report_task

# Gui hang loat 5 email
for i in range(5):
    send_email_task.delay(f'user{i}@example.com', f'Subject {i}', 'Body test')

# Gui 2 task xu ly anh
process_image_task.delay('photo1.jpg', 1920, 1080)
process_image_task.delay('photo2.jpg', 800, 600)

# Gui 1 task tao bao cao
generate_report_task.delay('traffic', '2026-01-01', '2026-06-03')

print('Da gui 8 tasks! Mo Flower va RabbitMQ Dashboard de quan sat.')
"
```

Sau khi chạy xong:
1. Nhấn F5 trên Flower → Tab Workers sẽ hiện `Processed: 8`, `Succeeded: 8`
2. Nhấn F5 trên RabbitMQ → Tab Overview sẽ có biểu đồ sóng tin nhắn rõ ràng
3. **Chụp ảnh ngay lập tức** cho báo cáo!

---

## 📝 TỔNG HỢP: CHECKLIST ẢNH CHỤP CẦN CÓ CHO PHẦN 3.4

| # | Nội dung ảnh | Mục báo cáo | Ưu tiên |
|---|-------------|-------------|---------|
| 1 | Terminal: `docker ps` hiện 3 container healthy | 3.4 (mở đầu) | ⭐ |
| 2 | Terminal Worker: Log khởi động + `worker1@... ready.` | 3.4.1 | ⭐⭐⭐ |
| 3 | Flower Dashboard: Worker Online, Processed = 0 | 3.4.1 | ⭐⭐ |
| 4 | Terminal Client: Gửi 3 task, nhận PENDING + task_id | 3.4.2 | ⭐⭐⭐ |
| 5 | Terminal Worker: Log nhận và xử lý 3 task tuần tự | 3.4.2 | ⭐⭐⭐ |
| 6 | Terminal Client: AsyncResult query → SUCCESS + kết quả JSON | 3.4.2 | ⭐⭐ |
| 7 | RabbitMQ Dashboard: Biểu đồ Message rates nhảy | 3.4.3 | ⭐⭐⭐ |
| 8 | RabbitMQ Dashboard: Tab Queues hiện 3 queue | 3.4.3 | ⭐⭐ |
| 9 | Flower Dashboard: Tab Workers — Processed/Succeeded có số | 3.4.3 | ⭐⭐⭐ |
| 10 | Flower Dashboard: Tab Tasks — Danh sách task SUCCESS | 3.4.3 | ⭐⭐⭐ |
