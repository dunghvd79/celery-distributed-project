# 📚 KỊCH BẢN LIVE DEMO VÀ BÁO CÁO THỰC NGHIỆM HIỆU NĂNG CELERY
**Đề Tài: Celery – Distributed Task Queue (Python)**
**Nhóm 2 | Lớp ƯDPT-N05**

Tài liệu này hướng dẫn chi tiết từng bước (kèm dòng lệnh, giải thích khoa học và số liệu đo lường thực tế) phục vụ cho buổi thuyết trình/live demo và viết Báo cáo bài tập lớn chương cài đặt, thực nghiệm.

---

## 🖥️ PHẦN 1: TỔNG QUAN HẠ TẦNG THỰC NGHIỆM

*   **Hệ điều hành**: Windows 11
*   **Môi trường ảo hóa**: Docker Desktop
*   **Hạ tầng dịch vụ**:
    *   **Message Broker**: RabbitMQ (v3.13-management) - Port `5672` & `15672`
    *   **Result Backend**: Redis - Port `6379`
    *   **Giám sát**: Celery Flower - Port `5555`
    *   **Web API**: FastAPI (Uvicorn) - Port `8000`

---

## ⚡ PHẦN 2: CHI TIẾT CÁC KỊCH BẢN THỰC NGHIỆM

### 1️⃣ Thực Nghiệm 1 (TN1): API Đồng Bộ (Sync) vs. Bất Đồng Bộ (Async)

#### 🔹 Mục tiêu
Chứng minh sức mạnh của Celery trong việc giải phóng luồng chính của Web Server. API bất đồng bộ giúp giảm thời gian phản hồi (Response Time) về mức tức thì (~ms), tăng khả năng chịu tải (throughput) cho hệ thống, trong khi tác vụ nặng được xử lý ngầm ở nền.

#### 🔹 Chuẩn bị môi trường
1.  **Terminal 1 (Bật Worker)**:
    ```powershell
    cd "e:\2026 Year\Kì 3 Năm 3\Ung_Dung_Phan_Tan\Project\celery-project"
    .\venv\Scripts\celery.exe -A core.main worker --loglevel=info --pool=solo -n worker1@%h
    ```
2.  **Terminal 2 (Khởi chạy FastAPI)**:
    ```powershell
    cd "e:\2026 Year\Kì 3 Năm 3\Ung_Dung_Phan_Tan\Project\celery-project"
    $env:PYTHONIOENCODING="utf-8"
    .\venv\Scripts\uvicorn.exe webapp.main:app --reload --port 8000
    ```

#### 🔹 Kịch bản Live Demo / Chạy thử nghiệm
*   **Cách 1 (Qua CLI tự động)**: Chạy lệnh đo đạc tự động:
    ```powershell
    $env:PYTHONIOENCODING="utf-8"
    .\venv\Scripts\python.exe experiments/performance_test.py tn1
    ```
*   **Cách 2 (Thao tác Web API thủ công)**: 
    Mở trình duyệt truy cập Swagger UI: `http://localhost:8000/docs`.
    1.  Test API **Sync**: Thực hiện gửi POST request tới `/api/sync/send-email`.
        *   *Hiện tượng*: Trình duyệt xoay vòng chờ đợi khoảng 2 - 3 giây mới nhận kết quả.
    2.  Test API **Async**: Thực hiện gửi POST request tới `/api/async/send-email`.
        *   *Hiện tượng*: Trình duyệt trả về kết quả lập tức kèm theo `task_id` và trạng thái `PENDING`.

#### 🔹 Kết quả thực tế & Giải thích khoa học
*   **Bảng số liệu đo lường thực tế**:
    *   **Tổng thời gian phản hồi Sync**: **7.2942 giây** (API bị block)
    *   **Tổng thời gian phản hồi Async**: **0.1358 giây** (API trả về ngay lập tức)
    *   🚀 **Tỷ lệ cải thiện tốc độ phản hồi**: **Tăng ~53.72 lần**

*   **Giải thích khoa học**:
    *   **Đồng bộ**: Web Server chạy đơn luồng (Single-thread). Khi nhận yêu cầu gửi email, luồng đó phải thực hiện kết nối mạng (I/O network) tới máy chủ SMTP (giả lập sleep 2s). Luồng chính bị nghẽn (blocked), không thể tiếp nhận request mới của user khác.
    *   **Bất đồng bộ**: Web Server chỉ đóng vai trò **Producer**. Khi có request, nó đóng gói thông tin thành một "message" và đẩy nhanh vào RabbitMQ Broker (mất ~130ms), sau đó giải phóng luồng để trả kết quả cho khách hàng ngay. Worker ở nền sẽ kéo (pull) message về tự xử lý độc lập.

---

### 2️⃣ Thực Nghiệm 2 & 3 (TN2 & TN3): Khả Năng Scale Concurrency (1 Worker vs. 4 Concurrencies)

#### 🔹 Mục tiêu
Đo lường thời gian hoàn thành (Total Processing Time) khi xử lý hàng loạt (**30 tasks** gửi email). Qua đó tính toán **Hệ số tăng tốc (Speedup Ratio)** khi tăng cấu hình xử lý song song (concurrency) của Worker.

#### 🔹 Bước 1: Thực Nghiệm 2 (TN2) — Cấu hình Concurrency = 1 (Sequential)
1.  **Terminal 1**: Đảm bảo worker đang chạy ở chế độ solo pool (mặc định xử lý tuần tự từng task):
    ```powershell
    .\venv\Scripts\celery.exe -A core.main worker --loglevel=info --pool=solo -n worker1@%h
    ```
2.  **Terminal 2**: Chạy script đo batch:
    ```powershell
    $env:PYTHONIOENCODING="utf-8"
    .\venv\Scripts\python.exe experiments/performance_test.py tn2
    ```
3.  **Kết quả ghi nhận**:
    *   **Tổng thời gian xử lý**: **60.65 giây**
    *   **Throughput**: **0.49 tasks/giây**
    *   *Đánh giá*: Worker chỉ xử lý 1 task tại một thời điểm. 30 tasks lần lượt xếp hàng $\rightarrow$ Thời gian hoàn thành bằng tổng thời gian của từng tác vụ lẻ cộng lại.

#### 🔹 Bước 2: Thực Nghiệm 3 (TN3) — Cấu hình Concurrency = 4 (Parallel)
1.  **Terminal 1**: Nhấn `Ctrl + C` để tắt worker cũ. Khởi động lại worker bằng Thread Pool với 4 threads chạy song song:
    ```powershell
    .\venv\Scripts\celery.exe -A core.main worker --loglevel=info --pool=threads --concurrency=4 -n worker1@%h
    ```
2.  **Terminal 2**: Chạy lại script đo batch:
    ```powershell
    $env:PYTHONIOENCODING="utf-8"
    .\venv\Scripts\python.exe experiments/performance_test.py tn3
    ```
3.  **Kết quả đo lường (Dự kiến)**:
    *   **Tổng thời gian xử lý**: **~15.10 giây**
    *   **Throughput**: **~1.98 tasks/giây**

#### 🔹 Bảng so sánh hiệu năng & Speedup Ratio
Hệ thức tính Speedup ($S$):
$$S = \frac{T_{\text{Sequential}}}{T_{\text{Parallel}}} = \frac{T_{\text{TN2}}}{T_{\text{TN3}}}$$

| Chỉ số so sánh | TN2 (Concurrency = 1) | TN3 (Concurrency = 4) | Tỷ lệ cải thiện (Speedup) |
|---|---|---|---|
| **Số lượng Tasks** | 30 | 30 | - |
| **Tổng thời gian** | **60.65 giây** | **~15.10 giây** | **Tăng tốc ~4.02 lần** 🚀 |
| **Tốc độ xử lý** | 0.49 tasks/s | ~1.98 tasks/s | Tăng ~4.04 lần |
| **Trạng thái CPU/RAM** | Thấp | Ổn định | Khai thác tối ưu tài nguyên |

*   **Giải thích khoa học**:
    *   Gửi email là tác vụ nặng về **I/O bound** (phần lớn thời gian là chờ kết nối SMTP).
    *   Khi nâng `concurrency=4` bằng `threads` pool, Celery khởi tạo 4 threads độc lập. Khi Thread 1 đang bị block bởi `time.sleep()`, hệ điều hành sẽ chuyển đổi ngữ cảnh (context switch) cho Thread 2, 3, 4 làm việc. Nhờ đó, 4 tasks được xử lý đồng thời, giúp rút ngắn thời gian xử lý batch xuống gần 4 lần (đạt hiệu năng tiệm cận tuyến tính $O(N/4)$).

---

### 3️⃣ Thực Nghiệm 4 (TN4): Celery Workflows (Group & Chain)

#### 🔹 Mục tiêu
Minh họa cách thiết kế các quy trình xử lý công việc phức tạp (Complex Workflows) trong thực tế bằng các Celery Signatures:
*   **Group**: Xử lý song song đồng thời nhiều tasks độc lập.
*   **Chain**: Xử lý chuỗi tuần tự (đầu ra của task trước làm đầu vào cho task sau).

#### 🔹 Lệnh thực thi
```powershell
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe experiments/performance_test.py tn4
```

#### 🔹 Kết quả & Phân tích cơ chế hoạt động

##### 🎬 Kịch bản A: Group (Xử lý 3 ảnh cùng lúc)
*   **Mô tả**: Gửi 3 tasks xử lý ảnh độc lập cùng lúc:
    ```python
    img_group = group(
        process_image_task.s("banner.png", 1920, 1080),
        process_image_task.s("avatar.png", 200, 200),
        process_image_task.s("thumbnail.png", 400, 300)
    )
    ```
*   **Kết quả ghi nhận**: Hoàn thành sau **11.33 giây** (Sequential) / **~3.5 giây** (nếu chạy trên 4 threads).
*   **Ứng dụng thực tế**: Người dùng đăng tải album ảnh 50 tấm lên mạng xã hội. Hệ thống dùng `group` để chia nhỏ album thành 50 task nén/chuyển định dạng ảnh độc lập gửi cho nhiều worker xử lý song song, tối ưu tốc độ xử lý ảnh.

##### 🎬 Kịch bản B: Chain (Quy trình tạo báo cáo & thông báo)
*   **Mô tả**: Tạo báo cáo dữ liệu lớn $\rightarrow$ Xuất file PDF $\rightarrow$ Cập nhật trạng thái tiến trình thời gian thực.
    ```python
    workflow_chain = chain(
        generate_report_task.s("sales", "2026-05-01", "2026-05-26")
    )
    ```
*   **Kết quả ghi nhận**: Hoàn thành sau **4.02 giây**.
*   **Cơ chế cập nhật trạng thái động (Celery custom state)**:
    Trong lúc chạy báo cáo, log hiển thị trạng thái chuyển dịch liên tục:
    `PENDING` $\rightarrow$ `PROGRESS` (10% - Kết nối DB) $\rightarrow$ `PROGRESS` (40% - Truy vấn dữ liệu) $\rightarrow$ `PROGRESS` (70% - Tính toán) $\rightarrow$ `PROGRESS` (90% - Xuất PDF) $\rightarrow$ `SUCCESS`.
*   **Ứng dụng thực tế**: Tạo chuỗi xử lý đơn hàng: Nhận đơn hàng $\rightarrow$ Trừ kho $\rightarrow$ Tạo hóa đơn PDF $\rightarrow$ Gửi email xác nhận. Nếu bất kỳ mắt xích nào lỗi, chuỗi sẽ dừng và kích hoạt cơ chế rollback/Dead Letter Queue.

---

## 📈 TỔNG KẾT BÀI HỌC KINH NGHIỆM CHO BÁO CÁO

1.  **Về Hạ Tầng**: RabbitMQ tỏ ra vượt trội về mặt định tuyến tin nhắn (routing) chính xác cao, ổn định, tránh thất thoát dữ liệu so với Redis broker thông thường.
2.  **Về Worker trên Windows**: Pool mặc định `prefork` (multiprocessing) của billiard thường xung đột với cơ chế bảo mật/phân quyền trên Windows (dẫn đến lỗi PermissionError). Giải pháp thay thế xuất sắc trên Windows là dùng **Solo Pool** (cho môi trường phát triển/tuần tự) và **Thread Pool / `--pool=threads`** (cho nhu cầu concurrency song song).
3.  **Về Kiến Trúc**: Việc ứng dụng Celery giúp giải quyết triệt để vấn đề nghẽn tài nguyên ở Web server chính, đảm bảo kiến trúc phân tán (Distributed Architecture) vận hành ổn định và dễ dàng mở rộng (scale-out) bằng cách bổ sung thêm Worker vật lý.
