import os
import uuid
import logging
import functools
from redis import Redis
from celery.exceptions import Ignore
from dotenv import load_dotenv

# Tải cấu hình từ .env
load_dotenv()

logger = logging.getLogger(__name__)

class DistributedLock:
    """
    Quản lý khóa phân tán (Distributed Lock) sử dụng Redis làm backend.
    Đảm bảo tính duy nhất và loại trừ tương hỗ (mutual exclusion) giữa các worker.
    """
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def acquire(self, lock_key: str, token: str, expire_seconds: int = 10) -> bool:
        """
        Thử thiết lập khóa phân tán.
        - lock_key: Tên khóa (Ví dụ: lock:payment:TXN_12345)
        - token: Token định danh duy nhất cho tiến trình giữ khóa (UUID)
        - expire_seconds: Thời gian sống (TTL) của khóa để tránh deadlock nếu worker crash.
        
        Trả về True nếu lấy khóa thành công, False nếu ngược lại.
        """
        # Sử dụng lệnh SET với nx=True (chỉ set nếu chưa tồn tại) và ex=expire_seconds (thiết lập TTL)
        # Đây là thao tác nguyên tử (atomic operation) để tránh Race Condition
        return bool(self.redis.set(lock_key, token, ex=expire_seconds, nx=True))

    def release(self, lock_key: str, token: str) -> bool:
        """
        Giải phóng khóa phân tán một cách nguyên tử sử dụng Lua script.
        Chỉ cho phép xóa khóa nếu token truyền vào trùng với token đang lưu trong Redis.
        Điều này ngăn chặn Worker A giải phóng nhầm khóa của Worker B khi Worker A bị chạy quá giờ.
        """
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = self.redis.eval(lua_script, 1, lock_key, token)
        return bool(result)

    def is_locked(self, lock_key: str) -> bool:
        """
        Kiểm tra xem khóa có đang tồn tại trong Redis hay không.
        """
        return bool(self.redis.exists(lock_key))


# Khởi tạo Redis Client toàn cục dựa trên REDIS_URL cấu hình
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(REDIS_URL)
lock_manager = DistributedLock(redis_client)


def lock_task(key_format: str, expire_seconds: int = 30, retry_on_fail: bool = False):
    """
    Decorator bọc ngoài Celery task để đảm bảo tác vụ chỉ chạy duy nhất 1 instance tại 1 thời điểm.
    
    Args:
        key_format (str): Định dạng tên khóa trong Redis. Ví dụ: 'lock:payment:{0}'
        expire_seconds (int): Thời gian tự động giải phóng khóa (TTL) nếu task gặp sự cố (mặc định 30s)
        retry_on_fail (bool): Nếu True, khi không lấy được khóa sẽ tự động xếp hàng lại task (retry) sau 5s.
                              Nếu False, sẽ bỏ qua task (Ignore) để tránh chạy trùng lặp.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Nhận dạng self (Celery Task instance) và tách các đối số thực tế của hàm
            # Khi Celery task được bind=True, đối số đầu tiên sẽ là self
            if args and hasattr(args[0], 'request'):
                task_self = args[0]
                actual_args = args[1:]
            else:
                task_self = None
                actual_args = args

            # Tạo khóa lock_key động dựa trên các đối số thực tế truyền vào hàm
            try:
                lock_key = key_format.format(*actual_args, **kwargs)
            except Exception:
                # Nếu format lỗi, dùng tên hàm kết hợp với hash của đối số để tránh trùng lặp
                lock_key = f"lock:{func.__name__}:{hash(str(actual_args))}:{hash(str(kwargs))}"

            token = str(uuid.uuid4())
            task_id = task_self.request.id if task_self else "N/A"
            task_name = task_self.name if task_self else func.__name__

            logger.info(f"Task {task_name}[{task_id}] đang yêu cầu khóa: {lock_key} (Token: {token})")

            # Thực hiện acquire khóa
            acquired = lock_manager.acquire(lock_key, token, expire_seconds=expire_seconds)

            if not acquired:
                logger.warning(
                    f"Task {task_name}[{task_id}] không thể lấy khóa {lock_key} "
                    f"vì tài nguyên đang được xử lý bởi một tác vụ khác."
                )
                if retry_on_fail and task_self:
                    # Đẩy task quay lại hàng đợi để thực thi lại sau 5 giây
                    logger.info(f"Task {task_name}[{task_id}] được xếp hàng chờ (retry) sau 5 giây...")
                    raise task_self.retry(countdown=5, max_retries=5)
                else:
                    # Bỏ qua tác vụ trùng lặp để tránh Race Condition (State: IGNORED)
                    logger.info(f"Task {task_name}[{task_id}] tự động hủy/bỏ qua (Ignore) để bảo vệ dữ liệu.")
                    raise Ignore()

            try:
                # Thực thi logic nghiệp vụ chính của task
                return func(*args, **kwargs)
            finally:
                # Giải phóng khóa một cách an toàn và nguyên tử
                released = lock_manager.release(lock_key, token)
                if released:
                    logger.info(f"Task {task_name}[{task_id}] đã giải phóng khóa thành công: {lock_key}")
                else:
                    logger.warning(
                        f"Task {task_name}[{task_id}] không thể giải phóng khóa {lock_key}. "
                        f"Khóa có thể đã tự động hết hạn (TTL) hoặc đã bị thay đổi."
                    )
        return wrapper
    return decorator
