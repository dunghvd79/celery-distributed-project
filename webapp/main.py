"""
webapp/main.py — FastAPI Web Application for Demo and Performance Testing (TN1)
"""
import time
import uuid
import os
from dotenv import load_dotenv

# Nạp các biến môi trường từ .env trước tiên
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult

from fastapi.responses import HTMLResponse


# Import Celery app và tasks từ core
from core.main import app as celery_app
from core.tasks import send_email_task, process_image_task

app = FastAPI(
    title="Celery Distributed Task Queue Demo API",
    description="API Endpoint cho thực nghiệm hiệu năng Celery và demo các tính năng nâng cao",
    version="1.0.0"
)

# Thêm CORS middleware để phục vụ giao diện (nếu có)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def read_root():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Dashboard file not found</h1>"


@app.get("/api/debug")
def debug_info():
    import celery
    return {
        "broker_url": celery_app.conf.broker_url,
        "result_backend": celery_app.conf.result_backend,
        "send_email_task_broker": send_email_task.app.conf.broker_url,
        "send_email_task_app_name": send_email_task.app.main,
        "send_email_task_app_default_queue": send_email_task.app.conf.task_default_queue,
        "current_app_name": celery.current_app.main,
        "current_app_default_queue": celery.current_app.conf.task_default_queue,
        "env_file_exists": os.path.exists(".env"),
        "cwd": os.getcwd()
    }





# ============================================================
# EXPERIMENT 1 (TN1): SYNCHRONOUS VS ASYNCHRONOUS EMAIL
# ============================================================

@app.post("/api/sync/send-email")
def send_email_sync(
    recipient: str = Query("user@gmail.com", description="Email người nhận"),
    subject: str = Query("Sync Subject", description="Tiêu đề"),
    body: str = Query("Sync Body", description="Nội dung")
):
    """
    Gửi email ĐỒNG BỘ (Blocking).
    API sẽ bị block cho đến khi tác vụ gửi email (sleep 1-3s) hoàn tất.
    """
    start_time = time.perf_counter()
    
    # Gọi hàm Python thông thường (.run() hoặc gọi trực tiếp đối tượng func gốc)
    # Ở đây dùng .__wrapped__ để lấy hàm python nguyên bản không qua Celery decorator
    result = send_email_task.__wrapped__(recipient, subject, body)
    
    elapsed_time = time.perf_counter() - start_time
    
    return {
        "mode": "synchronous (blocking)",
        "response_time_seconds": round(elapsed_time, 4),
        "result": result
    }


@app.post("/api/async/send-email")
def send_email_async(
    recipient: str = Query("user@gmail.com", description="Email người nhận"),
    subject: str = Query("Async Subject", description="Tiêu đề"),
    body: str = Query("Async Body", description="Nội dung")
):
    """
    Gửi email BẤT ĐỒNG BỘ (Non-blocking).
    API đẩy task vào RabbitMQ broker rồi phản hồi NGAY LẬP TỨC kèm theo task_id.
    """
    start_time = time.perf_counter()
    
    # Đẩy task vào Celery queue
    task_result = celery_app.send_task("core.tasks.send_email_task", args=[recipient, subject, body])
    
    elapsed_time = time.perf_counter() - start_time
    
    return {
        "mode": "asynchronous (non-blocking)",
        "response_time_seconds": round(elapsed_time, 4),
        "task_id": task_result.id,
        "status": task_result.status
    }


# ============================================================
# TASK QUERY ENDPOINT
# ============================================================

@app.get("/api/tasks/{task_id}/status")
def get_task_status(task_id: str):
    """
    Truy vấn trạng thái và kết quả của task trong Redis Backend một cách an toàn
    bằng cách đọc trực tiếp từ Redis, tránh lỗi deserialization Exception của Celery.
    """
    import json
    from redis import Redis
    
    redis_url = celery_app.conf.result_backend or "redis://localhost:6379/0"
    
    try:
        client = Redis.from_url(redis_url)
        meta_bytes = client.get(f"celery-task-meta-{task_id}")
        
        if not meta_bytes:
            return {
                "task_id": task_id,
                "status": "PENDING",
                "result": None
            }
            
        meta = json.loads(meta_bytes.decode('utf-8'))
        status = meta.get("status", "PENDING")
        result = meta.get("result")
        
        # Nếu result là thông tin ngoại lệ, format thành chuỗi
        if isinstance(result, dict) and "exc_type" in result:
            result = f"{result['exc_type']}: {result.get('exc_message', '')}"
            
        return {
            "task_id": task_id,
            "status": status,
            "result": result
        }
    except Exception as e:
        # Cơ chế Fallback
        try:
            res = AsyncResult(task_id, app=celery_app)
            status = res.status
            result = res.info
            if isinstance(result, Exception):
                result = str(result)
            return {
                "task_id": task_id,
                "status": status,
                "result": result
            }
        except Exception as fallback_err:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(fallback_err))


# ============================================================
# WORKFLOW ENDPOINTS (TN4)
# ============================================================


@app.post("/api/workflow/group")
def trigger_group():
    """
    Kích hoạt Group Workflow: Xử lý 3 ảnh song song.
    """
    # Đảm bảo context của celery_app được thiết lập đúng trong Uvicorn thread
    celery_app.set_current()
    celery_app.set_default()
    
    from celery import group
    from core.tasks import process_image_task
    
    g = group(
        process_image_task.s("banner.png", 1920, 1080),
        process_image_task.s("avatar.png", 200, 200),
        process_image_task.s("thumbnail.png", 400, 300)
    )
    group_result = g.apply_async()
    
    # Lấy danh sách task_ids con trong group
    task_ids = [res.id for res in group_result.children]
    
    return {
        "mode": "group (parallel workflows)",
        "group_id": group_result.id,
        "task_ids": task_ids
    }


@app.post("/api/workflow/chain")
def trigger_chain():
    """
    Kích hoạt Chain Workflow: Tạo báo cáo Sales tuần tự.
    """
    # Đảm bảo context của celery_app được thiết lập đúng trong Uvicorn thread
    celery_app.set_current()
    celery_app.set_default()
    
    from celery import chain
    from core.tasks import generate_report_task
    
    c = chain(
        generate_report_task.s("sales", "2026-05-01", "2026-05-26")
    )
    chain_result = c.apply_async()
    
    # Lấy danh sách task_ids trong chain (đi ngược từ kết quả cuối qua parent)
    task_ids = []
    curr = chain_result
    while curr:
        task_ids.append(curr.id)
        curr = curr.parent
    task_ids.reverse()  # Đổi thứ tự cho đúng trình tự chạy (đầu -> cuối)
    
    return {
        "mode": "chain (sequential workflows)",
        "chain_id": chain_result.id,
        "task_ids": task_ids
    }


# ============================================================
# CELERY WORKER PROCESS MANAGER
# ============================================================
import subprocess
import sys
import os

def kill_all_celery_workers():
    """
    Tìm và tiêu diệt triệt để tất cả các tiến trình Celery Worker đang chạy nền
    để tránh xung đột cổng hoặc khóa tệp log.
    """
    try:
        if os.name == 'nt':
            # Sử dụng PowerShell để tìm và kết thúc các tiến trình chạy Celery worker
            cmd = 'powershell -Command "Get-CimInstance Win32_Process -Filter \\"CommandLine like \'%celery%\' and CommandLine like \'%worker%\'\\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Trên Linux/Unix sử dụng pkill
            subprocess.run(["pkill", "-f", "celery.*worker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class WorkerManager:
    def __init__(self):
        self.process = None
        self.pool_type = None
        self.concurrency = None
        self.log_file = "celery_worker_web.log"

    def start(self, pool_type: str, concurrency: int) -> dict:
        # Dừng và dọn dẹp các worker cũ đang chạy nền (kể cả orphaned do reload)
        self.stop()
        kill_all_celery_workers()
        
        # Chạy Python ở chế độ không đệm (unbuffered -u) để log được ghi xuống đĩa ngay lập tức
        cmd = [sys.executable, "-u", "-m", "celery", "-A", "core.main", "worker", "--loglevel=info", "-Q", "default,high_priority,low_priority"]
        
        if pool_type == "solo":
            cmd.extend(["--pool", "solo"])
        else:
            cmd.extend(["--pool", "threads", "--concurrency", str(concurrency)])
            
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
        except Exception:
            pass
            
        try:
            log_f = open(self.log_file, "w", encoding="utf-8")
        except Exception as e:
            # Nếu tệp tin log bị khóa, fallback tạo tệp log ngẫu nhiên
            try:
                unique_log = f"celery_worker_web_{uuid.uuid4().hex[:8]}.log"
                log_f = open(unique_log, "w", encoding="utf-8")
                self.log_file = unique_log
            except Exception:
                log_f = open(os.devnull, "w")
            
        try:
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            self.process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
                env=env
            )
            self.pool_type = pool_type
            self.concurrency = concurrency
            return {
                "status": "success",
                "pid": self.process.pid,
                "pool_type": pool_type,
                "concurrency": concurrency
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def stop(self) -> dict:
        if not self.process or self.process.poll() is not None:
            return {"status": "success", "message": "Already stopped"}
            
        pid = self.process.pid
        try:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.process.terminate()
                self.process.wait(timeout=3)
        except Exception as e:
            pass
            
        self.process = None
        self.pool_type = None
        self.concurrency = None
        return {"status": "success", "pid": pid}

    def get_status(self) -> dict:
        if self.process and self.process.poll() is None:
            return {
                "status": "running",
                "pid": self.process.pid,
                "pool_type": self.pool_type,
                "concurrency": self.concurrency
            }
        return {"status": "stopped"}

    def get_logs(self, lines: int = 50) -> str:
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.readlines()
                    return "".join(content[-lines:])
            except Exception:
                return "Không thể đọc log file."
        return "Chưa có log file."

worker_mgr = WorkerManager()

@app.post("/api/worker/start")
def start_worker(pool_type: str = Query("solo"), concurrency: int = Query(4)):
    if concurrency < 1 or concurrency > 8:
        raise HTTPException(status_code=400, detail="Concurrency must be between 1 and 8")
    res = worker_mgr.start(pool_type, concurrency)
    if res["status"] == "error":
        raise HTTPException(status_code=500, detail=res["message"])
    return res

@app.post("/api/worker/stop")
def stop_worker():
    return worker_mgr.stop()

@app.get("/api/worker/status")
def get_worker_status():
    return worker_mgr.get_status()


@app.get("/api/worker/stats")
def get_worker_stats():
    """
    Truy vấn trực tiếp qua Celery Inspect để lấy Uptime, PID và thống kê
    số lượng tác vụ của từng tiến trình worker đang chạy.
    """
    try:
        celery_app.set_current()
        celery_app.set_default()
        
        # Thiết lập timeout ngắn để tránh API bị treo nếu không có worker nào online
        insp = celery_app.control.inspect(timeout=0.8)
        stats = insp.stats()
        
        if not stats:
            return {"online": False, "message": "Không tìm thấy worker hoạt động"}
            
        workers_data = []
        for worker_name, info in stats.items():
            workers_data.append({
                "name": worker_name,
                "pid": info.get("pid"),
                "uptime": info.get("uptime"),
                "pool": info.get("pool", {}),
                "total": info.get("total", {})
            })
            
        return {
            "online": True,
            "workers": workers_data
        }
    except Exception as e:
        return {"online": False, "error": str(e)}

@app.get("/api/worker/logs")
def get_worker_logs(lines: int = Query(50)):
    return {"logs": worker_mgr.get_logs(lines)}


# ============================================================
# FEATURE 1: DISTRIBUTED LOCK (TN5)
# ============================================================

@app.post("/api/payment/trigger")
def trigger_payment_demo(
    txn_id: str = Query("TXN_12345", description="Mã giao dịch"),
    amount: float = Query(500000.0, description="Số tiền")
):
    """
    Kích hoạt kịch bản thử nghiệm khóa phân tán (Distributed Lock).
    Gửi đồng thời 2 task trùng mã giao dịch (txn_id) và 1 task khác mã giao dịch (txn_unique).
    """
    celery_app.set_current()
    celery_app.set_default()
    
    txn_unique = f"TXN_UNIQUE_{uuid.uuid4().hex[:6].upper()}"
    
    # Task 1: Trùng khóa
    task1 = celery_app.send_task(
        "feature1_distributed_lock.tasks.process_payment_task",
        args=[txn_id, amount]
    )
    # Task 2: Trùng khóa (gửi ngay sau đó)
    task2 = celery_app.send_task(
        "feature1_distributed_lock.tasks.process_payment_task",
        args=[txn_id, amount]
    )
    # Task 3: Khác khóa
    task3 = celery_app.send_task(
        "feature1_distributed_lock.tasks.process_payment_task",
        args=[txn_unique, amount / 2]
    )
    
    return {
        "status": "triggered",
        "txn_duplicate": txn_id,
        "txn_unique": txn_unique,
        "task_ids": {
            "task_dup_1": task1.id,
            "task_dup_2": task2.id,
            "task_unique": task3.id
        }
    }


# ============================================================
# FEATURE 2: DEAD LETTER QUEUE & ALERTING (TN6)
# ============================================================

@app.post("/api/dlq/trigger")
def trigger_dlq_demo(
    data: str = Query("order_import_9999", description="Dữ liệu đồng bộ")
):
    """
    Kích hoạt kịch bản thử nghiệm Dead Letter Queue (DLQ).
    Gửi một flaky task lỗi kết nối bên thứ 3 và tự động retry 3 lần trước khi đẩy vào DLQ.
    """
    celery_app.set_current()
    celery_app.set_default()
    
    task = celery_app.send_task(
        "feature2_dlq_alerting.tasks.process_flaky_task",
        args=[data]
    )
    
    return {
        "status": "triggered",
        "task_id": task.id
    }


@app.get("/api/dlq/messages")
def get_dlq_messages_api():
    """
    Đọc tất cả các tin nhắn hiện có trong Dead Letter Queue (celery.dlq) mà không xóa (Requeue).
    """
    messages = get_dlq_messages_internal(ack=False)
    return {"count": len(messages), "messages": messages}


@app.post("/api/dlq/clear")
def clear_dlq_messages_api():
    """
    Đọc và giải phóng (Xóa / Ack) toàn bộ các tin nhắn trong celery.dlq.
    """
    messages = get_dlq_messages_internal(ack=True)
    return {"status": "cleared", "count": len(messages), "messages": messages}


def get_dlq_messages_internal(ack: bool = False):
    import logging
    logger_internal = logging.getLogger("webapp.dlq")
    from kombu import Connection, Queue, Exchange
    broker_url = celery_app.conf.broker_url
    messages = []
    temp_msgs = []
    try:
        with Connection(broker_url) as conn:
            dlx_exchange = Exchange('dlx', type='direct')
            dlq_queue = Queue('celery.dlq', exchange=dlx_exchange, routing_key='celery.dlq')
            with conn.SimpleQueue(dlq_queue) as simple_queue:
                while True:
                    try:
                        # Đọc nhanh tin nhắn lỗi với timeout ngắn
                        msg = simple_queue.get(block=True, timeout=0.3)
                        payload = msg.payload
                        headers = msg.headers
                        
                        # Parse args an toàn cho cả Celery v2 payload format
                        task_args = payload
                        if isinstance(payload, (list, tuple)) and len(payload) > 0:
                            if isinstance(payload[0], (list, tuple)):
                                task_args = payload[0][0] if len(payload[0]) > 0 else "N/A"
                            else:
                                task_args = payload[0]
                        
                        messages.append({
                            "id": headers.get("id", "N/A"),
                            "task": headers.get("task", "N/A"),
                            "args": task_args,
                            "death_reason": headers.get("x-death", [{}])[0].get("reason", "N/A")
                        })
                        if ack:
                            msg.ack()
                        else:
                            temp_msgs.append(msg)
                    except simple_queue.Empty:
                        break
                
                # Trả ngược lại các tin nhắn vào hàng đợi sau khi đã đọc hết
                if not ack:
                    for msg in temp_msgs:
                        msg.requeue()
    except Exception as e:
        logger_internal.error(f"Error reading DLQ: {e}")
    return messages

@app.on_event("shutdown")
def shutdown_event():
    worker_mgr.stop()

