"""
tasks.py — 3 task mẫu đại diện các use case thực tế

USE CASE:
  1. send_email_task    → Giả lập gửi email hàng loạt (I/O bound)
  2. process_image_task → Giả lập xử lý ảnh/resize (CPU bound)
  3. generate_report_task → Giả lập tạo báo cáo dữ liệu lớn (CPU + I/O)
"""
import time
import random
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


# ============================================================
# TASK 1: Gửi Email
# USE CASE: Newsletter, OTP, xác nhận đơn hàng
# ============================================================
@shared_task(
    bind=True,
    name="core.tasks.send_email_task",
    max_retries=3,
    default_retry_delay=5,
)
def send_email_task(self, recipient: str, subject: str, body: str) -> dict:
    """
    Giả lập gửi email bất đồng bộ.
    
    Args:
        recipient: Email người nhận
        subject: Tiêu đề email
        body: Nội dung email
    
    Returns:
        dict: Kết quả gửi email
    """
    try:
        logger.info(f"[EMAIL] Đang gửi tới {recipient}...")
        
        # Giả lập thời gian xử lý I/O (kết nối SMTP server)
        processing_time = random.uniform(1.0, 3.0)
        time.sleep(processing_time)
        
        # Giả lập 5% tỷ lệ lỗi (để test retry)
        if random.random() < 0.05:
            raise ConnectionError("SMTP server không phản hồi")
        
        result = {
            "status": "sent",
            "recipient": recipient,
            "subject": subject,
            "processing_time_s": round(processing_time, 2),
            "task_id": self.request.id,
        }
        logger.info(f"[EMAIL] ✅ Gửi thành công tới {recipient} ({processing_time:.2f}s)")
        return result

    except ConnectionError as exc:
        logger.error(f"[EMAIL] ❌ Lỗi kết nối, retry lần {self.request.retries + 1}...")
        raise self.retry(exc=exc, countdown=5)


# ============================================================
# TASK 2: Xử lý Ảnh
# USE CASE: Resize ảnh sau khi user upload, tạo thumbnail
# ============================================================
@shared_task(
    bind=True,
    name="core.tasks.process_image_task",
    max_retries=3,
    default_retry_delay=10,
)
def process_image_task(self, image_path: str, width: int, height: int) -> dict:
    """
    Giả lập xử lý ảnh (resize, compress, watermark).
    
    Args:
        image_path: Đường dẫn file ảnh gốc
        width: Chiều rộng mong muốn (px)
        height: Chiều cao mong muốn (px)
    
    Returns:
        dict: Thông tin ảnh sau khi xử lý
    """
    try:
        logger.info(f"[IMAGE] Đang xử lý: {image_path} → {width}x{height}px")
        
        # Giả lập thời gian xử lý CPU (resize, nén ảnh)
        processing_time = random.uniform(2.0, 5.0)
        time.sleep(processing_time)
        
        # Giả lập kết quả xử lý
        original_size_kb = random.randint(500, 5000)
        compressed_size_kb = int(original_size_kb * random.uniform(0.2, 0.5))
        
        result = {
            "status": "processed",
            "original_path": image_path,
            "output_path": image_path.replace(".", f"_{width}x{height}."),
            "dimensions": f"{width}x{height}",
            "original_size_kb": original_size_kb,
            "compressed_size_kb": compressed_size_kb,
            "compression_ratio": f"{(1 - compressed_size_kb/original_size_kb)*100:.1f}%",
            "processing_time_s": round(processing_time, 2),
            "task_id": self.request.id,
        }
        logger.info(f"[IMAGE] ✅ Xử lý xong {image_path} ({processing_time:.2f}s) "
                   f"- Nén {result['compression_ratio']}")
        return result

    except Exception as exc:
        logger.error(f"[IMAGE] ❌ Lỗi: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# TASK 3: Tạo Báo Cáo
# USE CASE: Export PDF, báo cáo doanh thu tháng, phân tích dữ liệu
# ============================================================
@shared_task(
    bind=True,
    name="core.tasks.generate_report_task",
    max_retries=2,
    default_retry_delay=30,
)
def generate_report_task(self, report_type: str, start_date: str, end_date: str) -> dict:
    """
    Giả lập tạo báo cáo dữ liệu lớn.
    
    Args:
        report_type: Loại báo cáo ('sales', 'traffic', 'inventory')
        start_date: Ngày bắt đầu (YYYY-MM-DD)
        end_date: Ngày kết thúc (YYYY-MM-DD)
    
    Returns:
        dict: Thông tin báo cáo đã tạo
    """
    try:
        logger.info(f"[REPORT] Đang tạo báo cáo {report_type} "
                   f"từ {start_date} đến {end_date}...")
        
        # Cập nhật tiến trình (Celery task state)
        self.update_state(state="PROGRESS", meta={"progress": 10, "step": "Kết nối database"})
        time.sleep(random.uniform(0.5, 1.0))
        
        self.update_state(state="PROGRESS", meta={"progress": 40, "step": "Truy vấn dữ liệu"})
        time.sleep(random.uniform(1.0, 3.0))
        
        self.update_state(state="PROGRESS", meta={"progress": 70, "step": "Tính toán thống kê"})
        time.sleep(random.uniform(1.0, 2.0))
        
        self.update_state(state="PROGRESS", meta={"progress": 90, "step": "Xuất file PDF"})
        time.sleep(random.uniform(0.5, 1.0))
        
        # Giả lập kết quả báo cáo
        total_records = random.randint(1000, 50000)
        
        result = {
            "status": "completed",
            "report_type": report_type,
            "period": f"{start_date} → {end_date}",
            "total_records": total_records,
            "output_file": f"reports/{report_type}_{start_date}_{end_date}.pdf",
            "file_size_kb": random.randint(50, 500),
            "task_id": self.request.id,
        }
        logger.info(f"[REPORT] ✅ Tạo xong báo cáo {report_type} "
                   f"({total_records} records)")
        return result

    except Exception as exc:
        logger.error(f"[REPORT] ❌ Lỗi: {exc}")
        raise self.retry(exc=exc)
