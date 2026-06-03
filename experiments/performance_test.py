"""
experiments/performance_test.py — Script thực hiện các thực nghiệm so sánh hiệu năng (TN1, TN2, TN3, TN4)
"""
import time
import sys
import os
import random
from celery import group, chain

# Đảm bảo import được thư mục root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import app as celery_app
from core.tasks import send_email_task, process_image_task, generate_report_task


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title.center(58)} ")
    print("=" * 60)


# ============================================================
# EXPERIMENT 1: TN1 — ĐỒNG BỘ VS BẤT ĐỒNG BỘ
# ============================================================
def run_tn1():
    print_header("THỰC NGHIỆM 1: ĐỒNG BỘ (SYNC) VS BẤT ĐỒNG BỘ (ASYNC)")
    
    recipient = "test_perf@gmail.com"
    subject = "Perf Test"
    body = "Checking response time"
    
    print("\n1. Thực thi ĐỒNG BỘ (Sync - Blocking):")
    print("   Đang gọi hàm trực tiếp 3 lần...")
    start_sync = time.perf_counter()
    for i in range(3):
        t_start = time.perf_counter()
        # Gọi hàm python gốc (không qua Celery queue)
        send_email_task.__wrapped__(recipient, f"{subject} {i}", body)
        t_elapsed = time.perf_counter() - t_start
        print(f"   - Lần {i+1}: Hoàn thành sau {t_elapsed:.4f} giây")
    sync_total = time.perf_counter() - start_sync
    print(f"   => TỔNG THỜI GIAN ĐỒNG BỘ: {sync_total:.4f} giây")
    
    print("\n2. Thực thi BẤT ĐỒNG BỘ (Async - Non-blocking):")
    print("   Đang gửi 3 tasks vào Celery Queue...")
    start_async = time.perf_counter()
    task_ids = []
    for i in range(3):
        t_start = time.perf_counter()
        # Gửi task bất đồng bộ
        res = send_email_task.delay(recipient, f"{subject} {i}", body)
        task_ids.append(res.id)
        t_elapsed = time.perf_counter() - t_start
        print(f"   - Gửi Task {i+1} (ID: {res.id}): Hoàn thành sau {t_elapsed:.4f} giây")
    async_total = time.perf_counter() - start_async
    print(f"   => TỔNG THỜI GIAN GỬI ASYNC (Response time): {async_total:.4f} giây")
    
    speedup = sync_total / async_total if async_total > 0 else 0
    print(f"\n✅ KẾT LUẬN TN1:")
    print(f"   - API Response Time giảm từ {sync_total:.4f}s xuống {async_total:.4f}s")
    print(f"   - Tốc độ phản hồi tăng: {speedup:.2f} lần!")
    print("   - Ghi chú: Hệ thống phản hồi ngay lập tức cho client, việc xử lý thực tế do Worker đảm nhận.")


# ============================================================
# EXPERIMENT 2 & 3: TN2 & TN3 — ĐO HIỆU NĂNG VỚI 1 WORKER VS NHIỀU WORKERS
# ============================================================
def run_tn2_tn3(num_tasks: int = 20):
    print_header(f"THỰC NGHIỆM 2 & 3: BATCH PROCESS {num_tasks} TASKS")
    
    print(f"Đang chuẩn bị gửi {num_tasks} tasks gửi email...")
    
    # Kiểm tra số lượng worker đang hoạt động
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.ping()
        if active_workers:
            print(f"✅ Các workers đang online: {list(active_workers.keys())}")
        else:
            print("⚠️ CẢNH BÁO: Không tìm thấy Worker nào đang chạy! Hãy bật Worker trước khi chạy test.")
    except Exception as e:
        print(f"⚠️ Không kiểm tra được trạng thái Worker: {e}")
        
    print("\nBắt đầu gửi tasks vào queue...")
    start_time = time.perf_counter()
    
    results = []
    for i in range(num_tasks):
        res = send_email_task.delay(f"user_{i}@example.com", f"Batch {i}", "Body message")
        results.append(res)
        
    print(f"Đã gửi xong {num_tasks} tasks. Đang theo dõi tiến độ xử lý...")
    
    completed = 0
    last_completed = -1
    
    while completed < num_tasks:
        completed = sum(1 for r in results if r.ready())
        if completed != last_completed:
            progress = (completed / num_tasks) * 100
            bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
            sys.stdout.write(f"\r   Tiến độ: |{bar}| {completed}/{num_tasks} tasks ({progress:.1f}%)")
            sys.stdout.flush()
            last_completed = completed
        if completed < num_tasks:
            time.sleep(0.5)
            
    total_time = time.perf_counter() - start_time
    print(f"\n\n✅ KẾT QUẢ ĐO LƯỜNG:")
    print(f"   - Tổng số tasks: {num_tasks}")
    print(f"   - Tổng thời gian hoàn thành: {total_time:.2f} giây")
    print(f"   - Tốc độ xử lý trung bình: {num_tasks / total_time:.2f} tasks/giây")
    print("\n📝 HƯỚNG DẪN SO SÁNH HIỆU NĂNG (TN2 vs TN3):")
    print("   1. Chạy test này khi Worker chạy 1 concurrency (e.g. --pool=solo). Ghi nhận tổng thời gian (TN2).")
    print("   2. Restart Worker với nhiều concurrency hoặc chạy nhiều Workers (e.g., mở 4 terminal chạy worker hoặc --pool=threads --concurrency=4).")
    print("   3. Chạy lại test này. Ghi nhận tổng thời gian (TN3).")
    print("   4. So sánh và tính Speedup = Thời gian (1 Worker) / Thời gian (N Workers).")


# ============================================================
# EXPERIMENT 4: TN4 — WORKFLOW (CHAIN & GROUP)
# ============================================================
def run_tn4():
    print_header("THỰC NGHIỆM 4: CELERY WORKFLOWS (CHAIN & GROUP)")
    
    print("\n1. Demo GROUP (Chạy song song nhiều tasks độc lập):")
    print("   Gửi group gồm 3 task xử lý ảnh khác nhau...")
    
    img_group = group(
        process_image_task.s("banner.png", 1920, 1080),
        process_image_task.s("avatar.png", 200, 200),
        process_image_task.s("thumbnail.png", 400, 300)
    )
    
    start_time = time.perf_counter()
    group_result = img_group.apply_async()
    
    print("   Group đã được gửi. Đang đợi tất cả ảnh xử lý xong...")
    # Chờ kết quả
    group_outputs = group_result.get()
    elapsed = time.perf_counter() - start_time
    
    print(f"   ✅ Tất cả task trong Group đã xong sau {elapsed:.2f} giây!")
    for idx, out in enumerate(group_outputs):
        print(f"     - Ảnh {idx+1}: {out['original_path']} → {out['dimensions']} (Nén: {out['compression_ratio']})")
        
    print("\n2. Demo CHAIN (Chuỗi liên kết các tasks tuần tự, đầu ra task trước là đầu vào task sau):")
    print("   Kịch bản: Tạo báo cáo doanh thu → Lấy file báo cáo gửi email cho Sếp.")
    
    # generate_report_task trả về dict có key "output_file"
    # send_email_task nhận (recipient, subject, body). 
    # Ta sẽ định nghĩa một task trung gian hoặc truyền tham số.
    # Để đơn giản, ta sẽ nối chuỗi bằng subtask có sẵn hoặc chỉ ra luồng dữ liệu.
    
    # Định nghĩa chuỗi task: 
    # Task 1: Tạo báo cáo sales
    # Task 2: Khi xong, in thông báo hoặc gửi email (để minh họa thứ tự)
    workflow_chain = chain(
        generate_report_task.s("sales", "2026-05-01", "2026-05-26"),
        # Celery chain mặc định truyền kết quả task trước vào tham số đầu của task sau.
        # Ở đây ta giả lập một chuỗi đơn giản
    )
    
    print("   Đang khởi động chuỗi Chain...")
    chain_start = time.perf_counter()
    chain_result = workflow_chain.apply_async()
    
    print("   Đang chờ Chain hoàn tất (Tạo báo cáo có nhiều bước tiến trình)...")
    
    # Theo dõi tiến trình qua Redis
    last_status = None
    while not chain_result.ready():
        # Kiểm tra trạng thái của task đầu tiên trong chain
        # Vì chain trả về AsyncResult của task cuối cùng, ta cần lấy chain_result để check
        status = chain_result.status
        if status != last_status:
            print(f"     - Trạng thái hiện tại của Chain: {status}")
            last_status = status
        time.sleep(1)
        
    chain_output = chain_result.get()
    chain_elapsed = time.perf_counter() - chain_start
    print(f"   ✅ Chuỗi Chain hoàn tất sau {chain_elapsed:.2f} giây!")
    print(f"     - Kết quả báo cáo tạo ra: {chain_output['output_file']}")
    print(f"     - Tổng số dòng dữ liệu: {chain_output['total_records']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python performance_test.py [tn1 | tn2 | tn3 | tn4 | all]")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "tn1":
        run_tn1()
    elif cmd in ["tn2", "tn3"]:
        # Chạy batch 30 tasks cho nhanh nhưng vẫn rõ ràng hiệu năng
        run_tn2_tn3(num_tasks=30)
    elif cmd == "tn4":
        run_tn4()
    elif cmd == "all":
        run_tn1()
        run_tn2_tn3(num_tasks=20)
        run_tn4()
    else:
        print(f"Lệnh '{cmd}' không hợp lệ. Chọn: tn1, tn2, tn4, all")
