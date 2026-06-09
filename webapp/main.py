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
    Truy vấn trạng thái và kết quả của task trong Redis Backend.
    """
    res = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": res.status,
        "result": None
    }
    
    if res.ready():
        response["result"] = res.result
    elif res.status == "PROGRESS":
        response["result"] = res.info  # Chứa metadata tiến trình tự định nghĩa
        
    return response


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

class WorkerManager:
    def __init__(self):
        self.process = None
        self.pool_type = None
        self.concurrency = None
        self.log_file = "celery_worker_web.log"

    def start(self, pool_type: str, concurrency: int) -> dict:
        # Stop existing first
        if self.process and self.process.poll() is None:
            self.stop()
            
        cmd = [sys.executable, "-m", "celery", "-A", "core.main", "worker", "--loglevel=info"]
        
        if pool_type == "solo":
            cmd.extend(["--pool", "solo"])
        else:
            cmd.extend(["--pool", "threads", "--concurrency", str(concurrency)])
            
        try:
            if os.path.exists(self.log_file):
                os.close(open(self.log_file, "a").close()) # release handle if any
                os.remove(self.log_file)
        except Exception:
            pass
            
        try:
            log_f = open(self.log_file, "w", encoding="utf-8")
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            self.process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags
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

@app.get("/api/worker/logs")
def get_worker_logs(lines: int = Query(50)):
    return {"logs": worker_mgr.get_logs(lines)}

@app.on_event("shutdown")
def shutdown_event():
    worker_mgr.stop()

