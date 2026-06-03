"""
celeryconfig.py — Cấu hình trung tâm cho Celery app
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# BROKER & BACKEND
# ============================================================
# Message Broker: RabbitMQ nhận task từ Producer và phân phối cho Worker
broker_url = os.getenv("CELERY_BROKER_URL", "amqp://admin:admin123@localhost:5672//")

# Result Backend: Redis lưu trạng thái và kết quả task
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# ============================================================
# SERIALIZATION
# ============================================================
# Dùng JSON để dễ debug và tương thích đa ngôn ngữ
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# ============================================================
# TIMEZONE
# ============================================================
timezone = "Asia/Ho_Chi_Minh"
enable_utc = True

# ============================================================
# TASK BEHAVIOR
# ============================================================
# Worker xác nhận task SAU khi xử lý xong (tránh mất task khi crash)
task_acks_late = True

# Không lưu kết quả của task không cần kết quả (tiết kiệm Redis)
task_ignore_result = False

# Thời gian giữ kết quả trong Redis (1 ngày)
result_expires = 86400

# Số lần retry mặc định khi task lỗi
task_max_retries = 3

# Thời gian chờ giữa các lần retry (giây)
task_default_retry_delay = 5

# ============================================================
# WORKER CONFIGURATION
# ============================================================
# Mỗi Worker nhận tối đa bao nhiêu task cùng lúc
worker_prefetch_multiplier = 1

# Số task Worker xử lý trước khi restart (tránh memory leak)
worker_max_tasks_per_child = 100

# ============================================================
# QUEUE CONFIGURATION
# ============================================================
# Định nghĩa các queue mặc định
task_default_queue = "default"
task_queues = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "high_priority": {
        "exchange": "high_priority",
        "routing_key": "high_priority",
    },
    "low_priority": {
        "exchange": "low_priority",
        "routing_key": "low_priority",
    },
}
