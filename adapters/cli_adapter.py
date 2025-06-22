
import asyncio
import logging
import functools
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from core.interfaces import IMessagePusher
from core.user_service import UserService
from core.admin import AdminService

# 导入所有必要的依赖项
from services.factories import PWVNRoleplayChatServiceFactory, GeneralChatServiceFactory
from services.llm_factory import initialize_global_llm
from services.news_service import NewsService
from services.scheduler_service import SchedulerService

# 配置基础日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 为 apscheduler 设置一个独立的 logger 以免过于嘈杂
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class CLIPusher(IMessagePusher):
    """
    一个实现了 IMessagePusher 接口的命令行版本。
    它的方法不会真的发送网络请求，而是将信息格式化后打印到控制台。
    """
    def __init__(self, prefix="[Pusher]"):
        self.prefix = prefix

    async def send_private_message(self, user_id: int, message: str) -> None:
        log_message = f"\n{self.prefix} ==> Sending private message to USER<{user_id}>:\n---\n{message}\n---"
        print(log_message)
        logging.info(f"Simulated sending private message to {user_id}.")

    async def send_group_message(self, group_id: int, message: str) -> None:
        log_message = f"\n{self.prefix} ==> Sending to GROUP<{group_id}>:\n---\n{message}\n---"
        print(log_message)
        logging.info(f"Simulated sending group message to {group_id}.")


async def cli_loop(user_service: UserService, user_id: int):
    """
    使用 asyncio.to_thread 的非阻塞 CLI 循环。
    """
    while True:
        try:
            # 将阻塞的 input() 函数放到一个独立的线程中执行
            # 这样就不会阻塞主线程的 asyncio 事件循环
            message = await asyncio.to_thread(input, f"\n{user_id}> ")

            if message.lower() in ('exit', 'quit'):
                break
            
            reply = await user_service.handle_message(user_id, message)
            
            print(f"Bot> {reply}")

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}")
            logging.error("CLI Adapter error", exc_info=True)


async def main():
    """
    命令行适配器主函数。
    """
    print("--- Command-Line Chat Adapter (with Pusher Simulation) ---")
    print("Initializing services...")

    # 1. 初始化应用所需的服务（完整模拟 run.py 的过程）
    initialize_global_llm()

    # 实例化 CLI 版本的 Pusher
    cli_pusher = CLIPusher()
    
    # 实例化所有服务，并将 cli_pusher 注入
    scheduler = AsyncIOScheduler()
    
    # 实例化所有服务，并将 cli_pusher 和 scheduler 注入
    news_service = NewsService()

    scheduler.start()
    
    scheduler_service = SchedulerService(
        news_service=news_service,
        scheduler=scheduler,  # 传入 scheduler 实例
        pusher=cli_pusher
    )
    admin_service = AdminService(scheduler_service=scheduler_service) # Admin 也可触发任务
    
    factories = {
        'pwvn': PWVNRoleplayChatServiceFactory(settings.PWVN_ROLES_CONFIG_PATH),
        'plain': GeneralChatServiceFactory(),
    }
    
    user_service = UserService(
        user_data_path=settings.USER_DATA_PATH,
        factories=factories,
        admin_service=admin_service
    )
    
    # 2. 启动后台服务
    scheduler_service.start()
    
    print("Initialization complete. Scheduler is running in the background.")
    print("Enter 'exit' or 'quit' to stop.")

    try:
        user_id_str = input("Please enter your user ID (e.g., 10001): ")
        user_id = int(user_id_str)
        print(f"Welcome, user {user_id}. You can start chatting now.")
    except (ValueError, EOFError):
        print("Invalid user ID. Exiting.")
        return

    # 3. 运行非阻塞的 CLI 交互循环
    await cli_loop(user_service, user_id)

    # 优雅地关闭调度器
    scheduler.shutdown()
    print("\nScheduler stopped. Goodbye!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting application.")