import logging
from celery import shared_task
from celery.exceptions import Reject, Ignore
from feature2_dlq_alerting.alerting import send_slack_alert

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    name="feature2_dlq_alerting.tasks.process_flaky_task",
    max_retries=3,
    acks_late=True, # Xác nhận muộn để có thể Reject
)
def process_flaky_task(self, data: str) -> str:
    """
    Tác vụ giả lập kết nối và đồng bộ dữ liệu với API bên thứ ba.
    Tác vụ có tỉ lệ lỗi cao (flaky) và được cấu hình đẩy vào DLQ khi thất bại hoàn toàn.
    """
    logger.info(f"[FLAKY TASK] 🔄 Bắt đầu đồng bộ dữ liệu: '{data}' (Lần thử {self.request.retries + 1}/4)")
    
    try:
        # Cố tình ném lỗi kết nối API bên thứ ba để mô phỏng sự cố mạng
        raise ConnectionError("Không thể kết nối đến máy chủ API bên thứ ba (Timeout).")
        
    except Exception as exc:
        # Nếu chưa vượt quá số lần thử lại tối đa (3 lần retry + 1 lần chạy đầu = 4 lần thử)
        if self.request.retries < self.max_retries:
            logger.warning(
                f"[FLAKY TASK] ⚠️ Thất bại lần {self.request.retries + 1}. "
                f"Đang xếp hàng thử lại sau 5 giây..."
            )
            # Thử lại task
            raise self.retry(exc=exc, countdown=5)
        else:
            # Task thất bại hoàn toàn sau khi đã hết lượt retry
            logger.error(
                f"[FLAKY TASK] ❌ Task {self.request.id} thất bại hoàn toàn sau "
                f"{self.max_retries + 1} lần thử. Bắt đầu xử lý đẩy vào DLQ..."
            )
            
            # 1. Gửi cảnh báo tự động lên Slack
            send_slack_alert(
                task_name=self.name,
                task_id=self.request.id,
                error_msg=str(exc),
                retries=self.request.retries + 1
            )
            
            # 2. Chủ động đẩy thông tin lỗi vào hàng đợi celery.dlq
            try:
                with self.app.connection_or_acquire() as conn:
                    from kombu import Queue
                    dlq_queue = Queue('celery.dlq')
                    producer = conn.Producer(serializer='json')
                    
                    # Đóng gói headers và payload đúng chuẩn để consumer đọc được
                    headers = {
                        "id": self.request.id,
                        "task": self.name,
                    }
                    payload = self.request.args
                    
                    producer.publish(
                        payload,
                        headers=headers,
                        routing_key='celery.dlq',
                        declare=[dlq_queue]
                    )
                logger.info(f"[FLAKY TASK] ✅ Đã chủ động đẩy tin nhắn lỗi của Task {self.request.id} vào hàng đợi celery.dlq.")
            except Exception as e:
                logger.error(f"[FLAKY TASK] ❌ Lỗi khi tự đẩy tin nhắn lỗi vào DLQ: {e}")
            
            # 3. Bỏ qua task này ở phía Celery (để tránh lưu kết quả lỗi đè lên Redis)
            raise Ignore()
