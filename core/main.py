"""
main.py — Khởi tạo Celery application
"""
from celery import Celery

# Tạo Celery app với tên "celery_project"
app = Celery("celery_project")

# Load toàn bộ cấu hình từ celeryconfig.py
app.config_from_object("core.celeryconfig")

# Tự động tìm và đăng ký tasks trong các module
# (Sẽ thêm feature1, feature2 khi triển khai ở Giai đoạn 3, 4)
app.autodiscover_tasks(["core"])

if __name__ == "__main__":
    app.start()
