"""
webapp/main.py — FastAPI Web Application for Demo and Performance Testing (TN1)
"""
import time
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult

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


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Celery Distributed Task Queue Demo API",
        "endpoints": {
            "sync_email": "/api/sync/send-email (blocking)",
            "async_email": "/api/async/send-email (non-blocking)",
            "task_status": "/api/tasks/{task_id}/status",
        }
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
    task_result = send_email_task.delay(recipient, subject, body)
    
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
