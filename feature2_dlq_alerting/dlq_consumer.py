import os
import sys
import logging
from kombu import Connection, Queue, Exchange

# Đảm bảo import được thư mục root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# Thiết lập log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dlq_consumer")

def read_dlq_messages():
    # Lấy thông tin kết nối từ biến môi trường
    broker_url = os.getenv("CELERY_BROKER_URL", "amqp://admin:admin123@localhost:5672//")
    
    DLX_NAME = "dlx"
    DLQ_NAME = "celery.dlq"
    
    logger.info("=" * 60)
    logger.info("  BẮT ĐẦU ĐỌC TIN NHẮN TỪ DEAD LETTER QUEUE (DLQ)  ".center(60))
    logger.info("=" * 60)
    logger.info(f"Kết nối tới RabbitMQ: {broker_url}")
    
    try:
        with Connection(broker_url) as conn:
            # Khai báo Exchange và Queue DLQ tương tự như cấu hình Celery
            dlx_exchange = Exchange(DLX_NAME, type='direct')
            dlq_queue = Queue(DLQ_NAME, exchange=dlx_exchange, routing_key=DLQ_NAME)
            
            # Sử dụng SimpleQueue để lấy tin nhắn ra ngoài
            with conn.SimpleQueue(dlq_queue) as simple_queue:
                # Đếm số lượng tin nhắn trong hàng đợi
                # Lấy số tin nhắn thực tế bằng cách duyệt qua hàng đợi
                count = 0
                while True:
                    try:
                        # Đọc tin nhắn với block=True để đợi RabbitMQ phản hồi (timeout 2 giây)
                        message = simple_queue.get(block=True, timeout=2.0)
                        count += 1
                        
                        logger.info(f"\n--- TIN NHẮN LỖI SỐ {count} ---")
                        # Giải mã thông điệp (Payload Celery)
                        payload = message.payload
                        # Lấy properties (headers chứa thông tin lỗi từ RabbitMQ)
                        headers = message.headers
                        
                        logger.info(f"  - Task ID: {headers.get('id', 'N/A')}")
                        logger.info(f"  - Tên Task: {headers.get('task', 'N/A')}")
                        logger.info(f"  - Tham số truyền vào (args): {payload[0] if payload else 'N/A'}")
                        
                        # Chi tiết lỗi do RabbitMQ DLX đính kèm vào header khi message bị reject
                        death_info = headers.get('x-death', [])
                        if death_info:
                            reason = death_info[0].get('reason', 'N/A')
                            logger.info(f"  - Lý do đẩy vào DLQ (Reject reason): {reason}")
                        
                        # Gửi xác nhận (Ack) để chính thức xóa tin nhắn bị lỗi ra khỏi DLQ
                        message.ack()
                        logger.info("  -> Đã xác nhận (Ack) và xóa tin nhắn lỗi khỏi DLQ.")
                        
                    except simple_queue.Empty:
                        break
                
                if count == 0:
                    logger.info("Không phát hiện tin nhắn lỗi nào trong hàng đợi celery.dlq.")
                else:
                    logger.info(f"\n✅ Đã đọc và giải phóng xong {count} tin nhắn lỗi khỏi DLQ!")
                
    except Exception as e:
        logger.error(f"❌ Có lỗi xảy ra khi truy cập DLQ: {e}")

if __name__ == "__main__":
    read_dlq_messages()
