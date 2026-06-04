"""
main.py — Khởi tạo Celery application
"""
import sys
import os
# Thêm thư mục root vào sys.path để đảm bảo Celery import được các package feature1, feature2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import Celery

# Tạo Celery app với tên "celery_project"
app = Celery("celery_project")

# Load toàn bộ cấu hình từ celeryconfig.py
app.config_from_object("core.celeryconfig")

# Tự động tìm và đăng ký tasks trong các module
app.autodiscover_tasks(["core", "feature1_distributed_lock", "feature2_dlq_alerting"])

if __name__ == "__main__":
    app.start()
