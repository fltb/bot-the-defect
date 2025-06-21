from apscheduler.schedulers.background import BackgroundScheduler
import logging

from config import settings
from core.interfaces import IMessagePusher
from services.news_service import NewsService

class SchedulerService:
    def __init__(self, news_service: NewsService, pusher: IMessagePusher):
        self._scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
        self._news_service = news_service
        self._pusher = pusher

    async def daily_rss_report_job(self):
        """
        [修改] 这是执行每日 RSS 报告任务的具体逻辑。
        """
        logging.info(f"Executing job: '{settings.NEWS_SCHEDULE_CONFIG['job_name']}'")
        
        # 1. 从 NewsService 获取报告内容
        report_content = await self._news_service.get_report()
        
        # 2. 获取目标群组
        target_groups = settings.NEWS_SCHEDULE_CONFIG.get("target_group_ids", [])
        if not target_groups:
            logging.warning("No target groups configured for news report. Job finished without sending.")
            return

        # 3. 使用 IMessagePusher 推送消息
        for group_id in target_groups:
            try:
                await self._pusher.send_group_message(group_id, report_content)
                logging.info(f"Successfully sent news report to group {group_id}.")
            except Exception as e:
                logging.error(f"Failed to send news report to group {group_id}: {e}")
        
        logging.info(f"Job '{settings.NEWS_SCHEDULE_CONFIG['job_name']}' finished.")

    def start(self):
        """启动调度器并添加所有配置的任务"""
        if settings.NEWS_SCHEDULE_CONFIG.get("enabled"):
            cfg = settings.NEWS_SCHEDULE_CONFIG
            self._scheduler.add_job(
                self.daily_rss_report_job, # [修改] 调用新的任务函数
                'cron',
                hour=cfg.get("hour"),
                minute=cfg.get("minute"),
                name=cfg.get("job_name")
            )
            logging.info(f"Scheduled job '{cfg['job_name']}' daily at {cfg['hour']}:{cfg['minute']}.")
        
        self._scheduler.start()
        logging.info("Scheduler service started.")
    
    def cleanup(self):
        self._scheduler.shutdown()