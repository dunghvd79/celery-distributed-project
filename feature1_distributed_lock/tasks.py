import time
import random
import logging
from celery import shared_task
from feature1_distributed_lock.lock_manager import lock_task

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    name="feature1_distributed_lock.tasks.process_payment_task",
    max_retries=5,
    default_retry_delay=5,
)
@lock_task("lock:payment:{0}", expire_seconds=15, retry_on_fail=False)
def process_payment_task(self, payment_id: str, amount: float) -> dict:
    """
    Giả lập xử lý thanh toán giao dịch. Tác vụ này được bảo vệ bởi khóa phân tán.
    Hai giao dịch có cùng payment_id không thể chạy song song cùng lúc.
    """
    logger.info(f"[PAYMENT] 💸 Bắt đầu xử lý giao dịch {payment_id} với số tiền {amount:,} VNĐ...")
    
    # Giả lập thời gian kết nối cổng thanh toán ngân hàng (I/O sleep)
    processing_time = random.uniform(3.0, 5.0)
    time.sleep(processing_time)
    
    result = {
        "status": "success",
        "payment_id": payment_id,
        "amount": amount,
        "processing_time_s": round(processing_time, 2),
        "task_id": self.request.id,
    }
    
    logger.info(f"[PAYMENT] ✅ Xử lý thành công giao dịch {payment_id} ({processing_time:.2f}s)")
    return result
