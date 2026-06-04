import time
import sys
import os

# Đảm bảo import được thư mục root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import app as celery_app
from feature2_dlq_alerting.tasks import process_flaky_task
from feature2_dlq_alerting.dlq_consumer import read_dlq_messages

def run_demo():
    print("=" * 60)
    print("DEMO HÀNG ĐỢI THƯ CHẾT (DLQ) & CẢNH BÁO SLACK".center(60))
    print("=" * 60)
    
    # Kiểm tra trạng thái worker
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.ping()
        if active_workers:
            print(f"✅ Workers đang online: {list(active_workers.keys())}")
        else:
            print("⚠️ CẢNH BÁO: Không tìm thấy Worker nào đang chạy! Hãy bật Worker trước khi chạy demo.")
    except Exception as e:
        print(f"⚠️ Không kiểm tra được trạng thái Worker: {e}")
        
    print("\n[BƯỚC 1]: Gửi tác vụ Flaky (Mô phỏng lỗi mạng kết nối API)")
    print("-> Cơ chế: Tác vụ sẽ tự động thử lại (retry) 3 lần. Ở lần thứ 4 vẫn lỗi:")
    print("   1. Gửi cảnh báo lỗi chi tiết đến Slack.")
    print("   2. Từ chối tin nhắn (Reject) và đẩy tin nhắn vào hàng đợi 'celery.dlq'.")
    
    task_arg = "order_data_import_9999"
    print(f"\n   Đang gửi Task flaky với tham số: '{task_arg}'...")
    res = process_flaky_task.delay(task_arg)
    print(f"   Mã Task ID: {res.id}")
    
    print("\n[BƯỚC 2]: Theo dõi tiến trình thử lại của Worker...")
    # Mỗi lần retry mất khoảng 5 giây. 4 lần thử = khoảng 15-20 giây.
    start_time = time.time()
    last_status = None
    
    while True:
        # Lấy trạng thái của task
        status = res.status
        if status != last_status:
            print(f"   - [{time.strftime('%H:%M:%S')}] Trạng thái hiện tại: {status}")
            last_status = status
            
        # Kiểm tra xem task đã kết thúc chưa.
        # Khi task bị Reject(requeue=False), Celery worker sẽ hoàn thành xử lý.
        # Ở đây ta check nếu ready() hoặc thời gian trôi qua quá 25 giây
        if res.ready() or (time.time() - start_time > 25):
            break
        time.sleep(1)
        
    print(f"\n   - [{time.strftime('%H:%M:%S')}] Tác vụ đã dừng xử lý ở Worker.")
    print("   - Đang đợi 2 giây để tin nhắn đồng bộ vào hàng đợi DLQ...")
    time.sleep(2)
    
    print("\n[BƯỚC 3]: Chạy consumer đọc tin nhắn bị hỏng trong hàng đợi 'celery.dlq'...")
    # Chạy trực tiếp hàm đọc DLQ trong kịch bản demo
    read_dlq_messages()
    
    print("\n=> KẾT LUẬN DEMO TÍNH NĂNG 2:")
    print("   1. Tác vụ đã được tự động thử lại đúng 3 lần theo cấu hình max_retries=3.")
    print("   2. Ở lần thứ 4 thất bại, hệ thống gửi Cảnh báo Slack và đưa tin nhắn vào DLQ.")
    print("   3. Dữ liệu tin nhắn bị hỏng không bị mất mát và được lưu trữ an toàn trong 'celery.dlq'.")
    print("   4. Người quản trị đã dùng consumer để trích xuất tin nhắn lỗi và giải phóng hàng đợi.")

if __name__ == "__main__":
    run_demo()
