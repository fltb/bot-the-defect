from functools import wraps
from config.settings import ADMIN_USER_IDS
from services.scheduler_service import SchedulerService # 假设可以访问调度器

class NotAdminError(Exception):
    """当用户不是管理员时抛出"""
    pass

def admin_required(func):
    """
    一个装饰器，用于检查命令调用者是否为管理员。
    它假设被装饰的方法的签名为 (self, user_id, ...)。
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 支持方法和函数两种形式
        # 如果是方法，第一个参数为 self，user_id 在 args[1]
        # 如果是函数，user_id 在 args[0]
        if len(args) >= 2:
            user_id = args[1]
        else:
            user_id = args[0]
        if user_id not in ADMIN_USER_IDS:
            raise NotAdminError(
                f"Permission denied. You are not an admin. You: {user_id}, Admins: {ADMIN_USER_IDS}"
            )
        return await func(*args, **kwargs)

    return wrapper


class AdminService:
    """封装所有管理员功能"""
    def __init__(self, scheduler_service: SchedulerService):
        self._scheduler = scheduler_service

    @admin_required
    async def reload_configs(self, user_id: int) -> str:
        """重新加载配置（伪代码）"""
        print(f"Admin {user_id} requested config reload.")
        # importlib.reload(config) # 简单粗暴的方式
        return "Configurations have been reloaded."

    @admin_required
    async def trigger_news_job_manually(self, user_id: int) -> str:
        """手动触发新闻任务"""
        print(f"Admin {user_id} triggered news job manually.")
        # apscheduler 允许你获取 job 并手动运行
        await self._scheduler.daily_rss_report_job()
        return "Daily news job has been triggered manually."
    
    async def handle_command(self, user_id: int, command: str) -> str:
        parts = command[1:].split(maxsplit=1)
        c = parts[1] if len(parts) > 1 else ''
        if c.startswith('triggernew'):
            return await self.trigger_news_job_manually(user_id)
        else:
            return "command not found."