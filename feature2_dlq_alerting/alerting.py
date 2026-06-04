import os
import json
import logging
import urllib.request
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def send_slack_alert(task_name: str, task_id: str, error_msg: str, retries: int) -> bool:
    """
    Gửi thông báo cảnh báo lỗi tự động tới kênh Slack thông qua Incoming Webhook.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    
    if not webhook_url or "YOUR/SLACK/WEBHOOK" in webhook_url:
        logger.warning(
            f"\n[SLACK ALERT SIMULATION] ⚠️ Chưa cấu hình Webhook URL thực tế trong file .env!\n"
            f"  - Task lỗi: {task_name}\n"
            f"  - Task ID: {task_id}\n"
            f"  - Số lần retry: {retries}\n"
            f"  - Chi tiết lỗi: {error_msg}\n"
            f"  -> Luồng tác vụ đã được đẩy vào Hàng đợi thư chết (Dead Letter Queue: celery.dlq)\n"
        )
        return False
        
    payload = {
        "text": f"🚨 *CẢNH BÁO HỆ THỐNG PHÂN TÁN: TÁC VỤ THẤT BẠI (DLQ)* 🚨\n"
                f"• *Tên Task*: `{task_name}`\n"
                f"• *Mã Task ID*: `{task_id}`\n"
                f"• *Số lần đã thử lại*: `{retries}`\n"
                f"• *Chi tiết lỗi*: `{error_msg}`\n"
                f"• *Trạng thái*: Đã tự động chuyển vào hàng đợi thư chết *`celery.dlq`* để xử lý thủ công."
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                logger.info(f"[SLACK ALERT] ✅ Đã gửi cảnh báo lỗi thành công lên kênh Slack.")
                return True
            else:
                logger.error(f"[SLACK ALERT] ❌ Slack trả về mã lỗi: {response.status}")
                return False
    except Exception as e:
        logger.error(f"[SLACK ALERT] ❌ Lỗi kết nối gửi cảnh báo tới Slack: {e}")
        return False
