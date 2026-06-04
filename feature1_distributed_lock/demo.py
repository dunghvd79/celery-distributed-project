import time
import sys
import os

# Đảm bảo import được thư mục root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import app as celery_app
from feature1_distributed_lock.tasks import process_payment_task

def run_demo():
    print("=" * 60)
    print("DEMO KHÓA PHÂN TÁN (DISTRIBUTED LOCK) VỚI REDIS".center(60))
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
        
    print("\n[KỊCH BẢN 1]: Gửi đồng thời 2 giao dịch Trùng Mã (Double Spending)")
    print("-> Yêu cầu: Giao dịch 1 chạy thành công, Giao dịch 2 bị từ chối do trùng lặp tài nguyên.")
    
    txn_dup = "TXN_DUPLICATE_12345"
    print(f"   Đang gửi Task 1: {txn_dup} số tiền 500,000 VNĐ...")
    res1 = process_payment_task.delay(txn_dup, 500000.0)
    
    print(f"   Đang gửi Task 2 (Trùng ID): {txn_dup} số tiền 500,000 VNĐ...")
    res2 = process_payment_task.delay(txn_dup, 500000.0)
    
    print("\n[KỊCH BẢN 2]: Gửi đồng thời 1 giao dịch Khác Mã (Chạy song song)")
    print("-> Yêu cầu: Chạy song song bình thường không bị ảnh hưởng.")
    txn_other = "TXN_UNIQUE_67890"
    print(f"   Đang gửi Task 3: {txn_other} số tiền 250,000 VNĐ...")
    res3 = process_payment_task.delay(txn_other, 250000.0)
    
    print("\nĐang theo dõi trạng thái các task...")
    time.sleep(1.5) # Chờ 1.5 giây để worker nhận task và xử lý bước lock ban đầu
    
    print(f"   - Trạng thái Task 1 ({txn_dup}): {res1.status}")
    print(f"   - Trạng thái Task 2 (Trùng - {txn_dup}): {res2.status}")
    print(f"   - Trạng thái Task 3 (Khác - {txn_other}): {res3.status}")
    
    print("\nĐang đợi các task hoàn thành...")
    
    # Vì một trong hai task trùng lặp (res1 hoặc res2) sẽ bị Ignore (bỏ qua),
    # Celery mặc định không ghi trạng thái của task bị Ignore vào Redis (để tối ưu hiệu năng),
    # khiến task đó giữ trạng thái mặc định PENDING mãi mãi.
    # Do đó ta chỉ cần đợi task thành công (res1 hoặc res2) và task độc lập res3 hoàn thành.
    while not ((res1.ready() or res2.ready()) and res3.ready()):
        time.sleep(1)
        
    print("\n✅ KẾT QUẢ CUỐI CÙNG TRÊN CLIENT:")
    status1 = res1.status
    status2 = res2.status
    desc1 = "Thành công (Đã lấy được khóa)" if status1 == "SUCCESS" else "Bị hủy ngầm (Ignore) do trùng khóa"
    desc2 = "Thành công (Đã lấy được khóa)" if status2 == "SUCCESS" else "Bị hủy ngầm (Ignore) do trùng khóa"
    
    print(f"   - Task 1 ({txn_dup}): Trạng thái = {status1} -> {desc1}, Kết quả = {res1.result}")
    print(f"   - Task 2 (Trùng - {txn_dup}): Trạng thái = {status2} -> {desc2}, Kết quả = {res2.result}")
    print(f"   - Task 3 (Khác - {txn_other}): Trạng thái = {res3.status} -> Thành công (Khác khóa), Kết quả = {res3.result}")
    
    print("\n=> ĐỂ XEM CHI TIẾT LOG: Bạn hãy kiểm tra cửa sổ Terminal chạy Worker (Terminal 1)!")

if __name__ == "__main__":
    run_demo()
