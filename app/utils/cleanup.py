from datetime import datetime

from app.config import FileConfig
from app.core.exception import logger
from app.docker.core.celery_app import CeleryManager
import shutil
from pathlib import Path


@CeleryManager.get_celery().task
def cleanup_directory(input_dir, output_dir):
    try:
        logger.info("[清理任务] 开始处理数据删除")
        # 清理输入目录
        input_path = Path(input_dir)
        if input_path.exists():
            shutil.rmtree(input_path)
            logger.info("清理输入目录成功: %s", input_dir)
        else:
            logger.warning("输入目录不存在，可能已被删除: %s", input_dir)

        # 清理输出目录
        output_path = Path(output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
            logger.info("清理输入目录成功: %s", output_dir)
        else:
            logger.warning("输出目录不存在，可能已被删除: %s", output_dir)
    except Exception as e:
        logger.error("清理失败: %s", str(e), exc_info=True)


# from datetime import datetime
#
# from app.docker.core.celery_app import CeleryManager
#
#
# @CeleryManager.get_celery().task
# def cleanup_temp_storage():
#     # 获取所有临时文件路径
#     temp_files = redis.smembers('temp_files')
#     for path in temp_files:
#         if (datetime.now() - get_upload_time(path)) > timedelta(hours=24):
#             # 移动到回收站（非直接删除）
#             recycle_path = move_to_recycle_bin(path)
#             # 记录回收站过期时间
#             redis.hset('recycle_files', recycle_path, datetime.now().timestamp())
#             redis.srem('temp_files', path)
#
# # 新增回收站清理任务（每周执行）
# @celery.task
# def cleanup_recycle_bin():
#     all_files = redis.hgetall('recycle_files')
#     for path, timestamp in all_files.items():
#         if (datetime.now() - datetime.fromtimestamp(timestamp)) > timedelta(days=7):
#             Path(path).unlink()
#             redis.hdel('recycle_files', path)
#
# @CeleryManager.get_celery().task
# def cleanup_temp_files():
#     """清理过期临时文件"""
#     # 清理目录
#     temp_root = Path(FileConfig.TEMP_STORAGE)
#     for date_dir in temp_root.iterdir():
#         if not date_dir.is_dir():
#             continue
#
#         # 检查目录日期是否超过保留期限
#         dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
#         if (datetime.now() - dir_date).days > 1:
#             shutil.rmtree(date_dir)
#             logger.info(f"清理临时目录: {date_dir}")
#
#     # 清理Redis记录（扫描所有temp_file:开头的key）
#     cursor = '0'
#     while cursor != 0:
#         cursor, keys = redis_conn.scan(
#             cursor=cursor,
#             match="temp_file:*",
#             count=100
#         )
#         for key in keys:
#             # 检查过期时间
#             ttl = redis_conn.ttl(key)
#             if ttl < 0:  # 已过期
#                 redis_conn.delete(key)
