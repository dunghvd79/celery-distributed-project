# Celery Distributed Task Queue Project

> **Bài tập lớn Môn Ứng dụng Phân tán** | Nhóm 2 | Lớp ƯDPT-N05

## 👥 Thành viên
- Hoàng Văn Dũng - 23010438
- Nguyễn Hữu Thành Đạt - 23040102

## 📌 Đề tài
**Celery – Distributed Task Queue (Python)**

Hệ thống xử lý tác vụ bất đồng bộ và phân tán sử dụng Celery với RabbitMQ làm Message Broker và Redis làm Result Backend. Dự án triển khai thêm 2 tính năng phân tán mới:
1. **Distributed Lock Manager** — Ngăn race condition khi nhiều Worker xử lý cùng một tác vụ
2. **Dead Letter Queue + Auto-Alerting** — Xử lý task lỗi bền vững và cảnh báo tự động qua Slack

## 🏗️ Kiến trúc hệ thống

```
[FastAPI App]  →  task.delay()  →  [RabbitMQ]  →  [Celery Workers]  →  [Redis]
 (Producer)                        (Broker)         (Consumers)         (Backend)
```

## ⚙️ Yêu cầu hệ thống
- Python >= 3.10
- Docker Desktop
- Git

## 🚀 Cài đặt & Chạy

### 1. Clone repository
```bash
git clone <repo-url>
cd celery-project
```

### 2. Copy file môi trường
```bash
copy .env.example .env
# Chỉnh sửa .env nếu cần
```

### 3. Khởi động hạ tầng (RabbitMQ + Redis + PostgreSQL)
```bash
docker compose up -d
```

### 4. Tạo virtual environment & cài packages
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 5. Chạy Celery Worker
```bash
celery -A core worker --loglevel=info
```

### 6. Chạy Flower Dashboard (giám sát)
```bash
celery -A core flower --port=5555
# Truy cập: http://localhost:5555
```

### 7. Chạy FastAPI App
```bash
uvicorn webapp.main:app --reload --port=8000
# Truy cập: http://localhost:8000/docs
```

## 📊 Các Dashboard

| Service | URL | Credentials |
|---|---|---|
| RabbitMQ Management | http://localhost:15672 | admin / admin123 |
| Flower (Celery Monitor) | http://localhost:5555 | - |
| FastAPI Docs | http://localhost:8000/docs | - |

## 📁 Cấu trúc Project

```
celery-project/
├── core/                       # Celery core setup
│   ├── celeryconfig.py         # Cấu hình Celery
│   ├── tasks.py                # Các task cơ bản
│   └── main.py                 # Khởi tạo Celery app
├── feature1_distributed_lock/  # Tính năng 1
│   ├── lock_manager.py         # DistributedLock class
│   ├── tasks.py                # Task có lock
│   └── demo.py                 # Script demo
├── feature2_dlq_alerting/      # Tính năng 2
│   ├── dlq_handler.py          # Dead Letter Queue handler
│   ├── alerting.py             # Slack/Email alerting
│   ├── tasks.py                # Task với retry + DLQ
│   └── demo.py                 # Script demo
├── webapp/                     # FastAPI application
│   └── main.py
├── docs/                       # Tài liệu & ảnh
│   ├── screenshots/
│   └── diagrams/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 📝 Tính năng

### Core Celery
- Xử lý tác vụ bất đồng bộ (email, image processing, report generation)
- Giám sát Worker qua Flower Dashboard
- Thực nghiệm so sánh hiệu năng đơn vs. đa Worker

### Feature 1: Distributed Lock (Redis)
- Ngăn nhiều Worker xử lý cùng tác vụ tại một thời điểm
- Auto-release lock khi Worker crash (TTL)
- API endpoint để kiểm tra trạng thái lock

### Feature 2: Dead Letter Queue + Alerting
- Tự động chuyển task lỗi (sau max_retries) vào DLQ
- Cảnh báo tự động qua Slack khi task vào DLQ
- Consumer để phân tích và replay task lỗi
