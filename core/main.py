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

# Cấu hình logging để ghi logs ra file celery_worker_web.log bằng UTF-8
from celery.signals import after_setup_logger, after_setup_task_logger
import logging

def configure_celery_logging(logger, *args, **kwargs):
    # Tránh add trùng handler
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename.endswith("celery_worker_web.log"):
            return
    try:
        fh = logging.FileHandler("celery_worker_web.log", mode="a", encoding="utf-8")
        formatter = logging.Formatter('[%(asctime)s: %(levelname)s/%(processName)s] %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        pass

after_setup_logger.connect(configure_celery_logging)
after_setup_task_logger.connect(configure_celery_logging)

# Tự động tìm và đăng ký tasks trong các module
app.autodiscover_tasks(["core", "feature1_distributed_lock", "feature2_dlq_alerting"])

if __name__ == "__main__":
    app.start()
