# celery_config.py
from celery import Celery

app = Celery('libyear_tasks',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0',
             include=['tasks.data_sync', 'tasks.analysis'])

# 配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_routes={
        'tasks.data_sync.*': {'queue': 'data_sync'},
        'tasks.analysis.*': {'queue': 'analysis'},
    },
    beat_schedule={
        # 增量同步 - 每6小时
        'incremental-sync-every-6-hours': {
            'task': 'tasks.data_sync.incremental_sync_all',
            'schedule': 3600 * 6,  # 6小时
        },
        # 全量同步 - 每天凌晨2点
        'full-sync-daily': {
            'task': 'tasks.data_sync.full_sync_all', 
            'schedule': crontab(hour=2, minute=0),
        },
        # 统计计算 - 每天凌晨3点
        'calculate-stats-daily': {
            'task': 'tasks.analysis.calculate_daily_stats',
            'schedule': crontab(hour=3, minute=0),
        },
    }
)