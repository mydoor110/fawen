"""
审批超时检测定时任务
Author: AI Assistant
Date: 2026-02-15

使用方法:
1. 添加到crontab(Linux/Mac):
   */30 * * * * cd /path/to/fawen && python scripts/check_approval_timeout.py

2. 添加到Windows任务计划程序:
   - 每30分钟执行一次此脚本

3. 或使用APScheduler在主应用中运行(推荐)
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.services.approval_timeout_service import ApprovalTimeoutService
from loguru import logger


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始检查审批超时任务...")
    
    db = SessionLocal()
    try:
        # 1. 检查并处理已超时的任务
        timeout_stats = ApprovalTimeoutService.check_and_handle_timeouts(db)
        logger.info(f"超时处理统计: {timeout_stats}")
        
        # 2. 检查即将超时的任务(提前3天提醒)
        upcoming_tasks = ApprovalTimeoutService.check_upcoming_timeouts(db, remind_days=3)
        logger.info(f"发送提前提醒: {len(upcoming_tasks)} 个任务")
        
        # 3. 检查即将超时的任务(提前1天提醒)
        upcoming_tasks_1d = ApprovalTimeoutService.check_upcoming_timeouts(db, remind_days=1)
        logger.info(f"发送最后提醒: {len(upcoming_tasks_1d)} 个任务")
        
        logger.info("审批超时检查完成!")
        
    except Exception as e:
        logger.error(f"执行审批超时检查时出错: {e}", exc_info=True)
        return 1
    finally:
        db.close()
    
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
