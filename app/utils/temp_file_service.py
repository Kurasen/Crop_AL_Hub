import hashlib
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict

from app.config import FileConfig
from app.core.exception import ValidationError, logger
from app.core.redis_connection_pool import redis_pool
from app.docker.core.celery_app import CeleryManager
from app.exts import db
from app.model.model_service import ModelService
from app.user.user_service import UserService
from app.utils.image_url_utils import ImageURLHandlerUtils
from app.utils.storage import storage, FileStorage


def remove_empty_parents_safely(file_path: Path, stop_at: Path, max_retries: int = 3):
    """
    安全删除空目录链（带并发检查和重试机制）

    参数:
        file_path: 被删除文件的路径
        stop_at: 停止删除的父目录（包含该目录本身）
        max_retries: 目录操作最大重试次数
    """
    current_dir = file_path.parent

    while current_dir != stop_at and current_dir.is_relative_to(stop_at):
        logger.debug(f"▶ 开始处理目录: {current_dir}")

        # 重试机制应对短暂的文件系统延迟
        for attempt in range(max_retries):
            try:
                if not any(current_dir.iterdir()):
                    logger.debug(f"↘ 尝试删除空目录（第{attempt + 1}次尝试）: {current_dir}")
                    current_dir.rmdir()
                    logger.info(f"🗑️ 成功删除空目录: {current_dir}")
                    break
                else:
                    logger.warning(f"⚠️ 目录非空，停止向上删除: {current_dir}")
                    return
            except FileNotFoundError:
                logger.debug(f"↗ 目录已被其他进程删除: {current_dir}")
                break
            except PermissionError as e:
                logger.error(f"⛔ 目录权限错误: {current_dir} - {str(e)}")
                return
            except OSError as e:
                if attempt == max_retries - 1:
                    logger.warning(f"⚠️ 删除目录失败（已达最大重试次数）: {current_dir} - {str(e)}")
                    return
                logger.debug(f"↻ 遇到暂时性错误，准备重试: {current_dir} - {str(e)}")
                time.sleep(0.5 * (attempt + 1))
        else:
            return

        # 向上移动一级目录（使用解析后的绝对路径避免符号链接问题）
        parent_dir = current_dir.resolve().parent
        if parent_dir == current_dir.resolve():
            logger.debug("⏹ 到达根目录，停止处理")
            break
        current_dir = parent_dir


class TempFileService:
    def __init__(self):
        self.storage = storage
        self.redis = redis_pool

    @staticmethod
    @contextmanager
    def _get_redis_conn():
        """复用Redis连接管理"""
        with redis_pool.get_redis_connection('files') as conn:
            yield conn

    def save_temp(self, file, upload_type: str, data_id: int, file_type: str, user_id: int) -> str:
        """保存到临时目录并生成URL"""
        # 生成文件哈希（使用文件内容）
        logger.info(f"upload_type: {upload_type}, file_type: {file_type}, data_id: {data_id}, file: {file}")

        file_content = file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        file.seek(0)

        logger.info(f"✅ 计算的文件哈希: {file_hash}")
        logger.info(f"✅ 保存的文件名: {file_hash}{Path(file.filename).suffix}")

        # 构建临时目录路径（复用正式目录模板）
        temp_dir = Path(FileConfig.TEMP_DIR) / FileConfig.UPLOAD_CONFIG[upload_type]['subdirectory'].format(
            file_type=file_type,
            data_id=data_id,
            user_id=user_id
        )
        logger.info(f"temp_dir: {temp_dir}")

        # 保存到临时目录（复用你的FileStorage）
        saved_path = self.storage.save_upload(
            file_stream=file,
            save_dir=temp_dir,
            file_name=f"{file_hash}{Path(file.filename).suffix}"
        )
        logger.info(f"saved_path: {saved_path}")

        saved_file_path = Path(saved_path) / f"{file_hash}{Path(file.filename).suffix}"
        logger.info(f"✅ 完整文件路径: {saved_file_path}")

        # 记录Redis
        with self.redis.get_redis_connection('files') as conn:
            key = f"temp:{user_id}:{upload_type}:{data_id}:{file_type}:{file_hash}"
            conn.hmset(key, {
                "real_path": str(saved_file_path),
                "user_id": str(user_id),
                "status": "pending",
                "expire_at": str(time.time() + 45)  # 7天
            })
            logger.info(f"当前时间:{time.time()}, 过期时间：:{time.time() + 45}")
            #conn.expire(key, 120)  # 原为7天（604800秒）

            logger.info(f"✅ 保存到Redis的键: {key}")
            logger.info(f"✅ 文件哈希: {file_hash}")
            logger.info(f"✅ 保存路径: {saved_path}")

        # 获取相对于 TEMP_DIR 的路径
        relative_path = Path(saved_path).relative_to(FileConfig.TEMP_DIR)

        # 生成URL路径（使用实际存储路径结构）
        url_path = f"{FileConfig.TEMP_BASE_URL}/{relative_path}/{file_hash}{Path(file.filename).suffix}"
        logger.info(f"✅ 生成的URL路径: {url_path}")

        return url_path

    def commit_from_temp(self, temp_url: str, user_id: int) -> bool:
        """从临时URL提交文件（其他接口调用）"""
        # 解析URL参数
        try:
            # 使用工具类验证和解析URL
            ImageURLHandlerUtils.validate_photo_file(temp_url)
            url_components = ImageURLHandlerUtils.parse_temp_url_components(temp_url)
            redis_key = ImageURLHandlerUtils.build_temp_redis_key(url_components)

            # 记录调试日志
            logger.debug(f"解析结果: {url_components}")

            # Redis验证
            with self.redis.get_redis_connection('files') as conn:
                file_info = conn.hgetall(redis_key)
                logger.debug(f"Redis返回数据: {file_info} | 类型: {type(file_info)}")

                if not isinstance(file_info, dict):
                    logger.error(f"Redis数据格式错误，期望字典，实际得到: {type(file_info)}")
                    raise ValidationError("文件元数据损坏")

                if not file_info:
                    logger.error(f"Redis键不存在: {redis_key}")
                    raise ValidationError("文件不存在或已过期")

                if 'user_id' not in file_info:
                    logger.error(f"Redis记录缺少user_id字段: {file_info}")
                    raise ValidationError("文件元数据不完整")

                if file_info.get('user_id') != str(user_id):
                    logger.warning(
                        f"用户权限验证失败: Redis.user_id={file_info.get('user_id')} vs Current.user_id={user_id}")
                    raise ValidationError("无操作权限")

                if file_info.get('status') == 'committed':
                    logger.warning(f"文件重复提交: {redis_key}")
                    raise ValidationError("文件已提交")

                # 更新状态
                conn.hset(redis_key, "status", "processing")
                logger.info(f"状态更新为processing: {redis_key}")

            # 异步转移文件
            self._move_to_final.delay(
                redis_key=redis_key,
                src_path=file_info['real_path'],
                upload_type=url_components['upload_type'],
                data_id=url_components['data_id'],
                file_type=url_components['file_type'],
                user_id=user_id
            )
            logger.info(f"✅ 解析得到的参数: {url_components}")
            logger.info(f"✅ 生成的Redis键: {redis_key}")

            return True
        except ValidationError as e:
            logger.error("文件验证失败：%s", str(e))
            raise e
        except Exception as e:
            logger.error("提交文件时发生未捕获的异常: %s", str(e), exc_info=True)
            raise e

    @staticmethod
    @CeleryManager.get_celery().task(bind=True)
    def _move_to_final(self, redis_key: str, src_path: str, upload_type: str, data_id: int, file_type: str,
                       user_id: int):
        """原子化文件转移操作（增强健壮性）"""
        try:
            # ========== 1. 初始化检查 ==========
            from myapp import create_app
            app = create_app()  # 创建Flask上下文

            # ========== 2. 前置状态验证 ==========
            with redis_pool.get_redis_connection('files') as conn:
                # 检查Redis键是否存在，防止重复处理
                if not conn.exists(redis_key):
                    logger.warning(f"⏩ 跳过已处理的任务: {redis_key}")
                    return

                # 获取文件信息
                file_info = conn.hgetall(redis_key)
                if file_info.get('status') == 'committed':
                    logger.warning(f"⏩ 文件已提交: {redis_key}")
                    return

                # 标记为处理中（防止并发）
                conn.hset(redis_key, "status", "processing")

            # ========== 3. 文件操作 ==========
            src_file = Path(src_path)
            if not src_file.exists():
                logger.error(f"⛔ 源文件不存在: {src_path}")
                with redis_pool.get_redis_connection('files') as conn:
                    conn.delete(redis_key)  # 清理无效键
                return

            # 3.1 移动文件到正式目录
            # 构建正式目录
            final_subdir = FileConfig.UPLOAD_CONFIG[upload_type]['subdirectory'].format(
                file_type=file_type,
                data_id=data_id,
                user_id=user_id
            )

            final_dir = Path(FileConfig.LOCAL_FILE_BASE) / "user_data" / final_subdir
            final_dir.mkdir(parents=True, exist_ok=True)
            final_file_path = final_dir / src_file.name

            # 使用文件流避免占用文件锁
            with open(src_path, 'rb') as src_stream:
                FileStorage.save_upload(
                    file_stream=src_stream,
                    save_dir=final_dir,
                    file_name=src_file.name
                )

            # 3.2 删除临时文件及目录
            try:
                src_file.unlink(missing_ok=True)  # 兼容Python 3.8+
                remove_empty_parents_safely(
                    file_path=src_file,
                    stop_at=Path(FileConfig.TEMP_DIR).resolve(),
                    max_retries=3
                )
            except Exception as e:
                logger.error(f"⛔ 文件删除失败: {str(e)}")
                raise  # 抛出异常触发重试

            #========== 4. 数据库更新 ==========
            relative_path = str(final_file_path.relative_to(FileConfig.LOCAL_FILE_BASE))

            database_mapping = {
                "model": {
                    "icon": (ModelService.get_model_by_id, "icon")  # (模型查询方法, 字段名)
                },
                "user": {
                    "avatars": (UserService.get_user_by_id, "avatar")
                }
            }

            # 在应用上下文中更新数据库
            with app.app_context():
                try:
                    # 更新数据库
                    if upload_type in database_mapping and file_type in database_mapping[upload_type]:
                        get_func, field = database_mapping[upload_type][file_type]
                        instance = get_func(data_id)
                        setattr(instance, field, relative_path)
                        db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"⛔ 数据库更新失败: {str(e)}")
                    raise  # 抛出异常触发重试

            # ========== 5. 最终清理 ==========
            with redis_pool.get_redis_connection('files') as conn:
                conn.delete(redis_key)  # 关键：成功后才删除键
                logger.info(f"✅ 完成迁移: {redis_key}")

        except FileNotFoundError as e:
            # 6. 文件不存在时的专用处理
            logger.error(f"🛑 文件已删除，终止任务: {src_path}")
            with redis_pool.get_redis_connection('files') as conn:
                conn.delete(redis_key)  # 确保清理残留
            return  # 直接返回，不重试
        except Exception as e:
            # 7. 其他错误处理
            logger.error(f"迁移失败: {str(e)}")
            with redis_pool.get_redis_connection('files') as conn:
                conn.hset(redis_key, "status", "error")
            raise self.retry(exc=e, countdown=60, max_retries=2)  # 有限重试

    # @staticmethod
    # @CeleryManager.get_celery().task(bind=True)
    # def _move_to_final(self, redis_key: str, src_path: str, upload_type: str, data_id: int, file_type: str,
    #                    user_id: int):
    #     """异步移动文件到正式区"""
    #     try:
    #         # 导入Flask应用工厂并创建上下文
    #         from myapp import create_app
    #         app = create_app()
    #
    #         # 构建正式目录
    #         final_subdir = FileConfig.UPLOAD_CONFIG[upload_type]['subdirectory'].format(
    #             file_type=file_type,
    #             data_id=data_id,
    #             user_id=user_id
    #         )
    #         final_dir = Path(FileConfig.LOCAL_FILE_BASE) / "user_data" / final_subdir
    #         final_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    #
    #         # 生成文件名（从源路径提取）
    #         file_name = Path(src_path).name  # 如 61a26a72c6283f97dde68f53ce2c2c41.jpg
    #         logger.info(f"final_dir: {final_dir}")
    #         final_file_path = final_dir / file_name
    #
    #         # 移动文件
    #         with open(src_path, 'rb') as f:
    #             saved_path = FileStorage.save_upload(
    #                 file_stream=f,
    #                 save_dir=final_dir,
    #                 file_name=Path(src_path).name
    #             )
    #
    #         src_file = Path(src_path)
    #         if src_file.exists():
    #             # 删除源文件
    #             try:
    #                 src_file.unlink()
    #                 logger.info(f"🗑️ 删除源文件: {src_file}")
    #
    #                 # 安全清理目录
    #                 remove_empty_parents_safely(
    #                     file_path=src_file,
    #                     stop_at=Path(FileConfig.TEMP_DIR).resolve(),
    #                     max_retries=3
    #                 )
    #             except Exception as e:
    #                 logger.error(f"⛔ 文件删除失败: {src_file} - {str(e)}")
    #
    #         relative_path = str(final_file_path.relative_to(FileConfig.LOCAL_FILE_BASE))
    #
    #         database_mapping = {
    #             "model": {
    #                 "icon": (ModelService.get_model_by_id, "icon")  # (模型查询方法, 字段名)
    #             },
    #             "user": {
    #                 "avatars": (UserService.get_user_by_id, "avatar")
    #             }
    #         }
    #
    #         # 在应用上下文中更新数据库
    #         with app.app_context():
    #             # 更新数据库（完全复用你原有的逻辑）
    #             if upload_type in database_mapping and file_type in database_mapping[upload_type]:
    #                 get_func, field = database_mapping[upload_type][file_type]
    #                 instance = get_func(data_id)
    #                 setattr(instance, field, relative_path)
    #                 db.session.commit()
    #
    #         # 清理记录
    #         with redis_pool.get_redis_connection('files') as conn:
    #             conn.delete(redis_key)
    #         Path(src_path).unlink()
    #     except Exception as e:
    #         # 错误处理
    #         with redis_pool.get_redis_connection('files') as conn:
    #             conn.hset(redis_key, "status", "error")
    #         raise self.retry(exc=e, countdown=60, max_retries=3)


temp_service = TempFileService()


@CeleryManager.get_celery().task(bind=True)
def cleanup_temp_files(self):
    logger.info("🚀 开始执行临时文件清理任务")
    try:
        with redis_pool.get_redis_connection('files') as conn:
            cursor = '0'
            deleted_count = 0
            total_scanned = 0  # 统计扫描的键数量
            while True:
                cursor, keys = conn.scan(cursor, match='temp:*', count=100)
                logger.info(f"🔍 扫描到 {len(keys)} 个键，cursor={cursor}")  # 新增日志
                total_scanned += len(keys)
                if not keys and cursor == 0:  # 退出条件：无键且游标归零
                    break

                for key in keys:
                    try:
                        # 确保每次循环都初始化变量
                        file_path_str = None
                        file_path_obj = None

                        expire_at = conn.hget(key, 'expire_at')
                        file_path_str = conn.hget(key, 'real_path')
                        logger.debug(f"检查键: {key}, expire_at={expire_at}")
                        # 条件判断和路径转换
                        if expire_at and float(expire_at) < time.time():
                            if file_path_str:
                                file_path_obj = Path(file_path_str)
                                logger.debug(f"处理过期键: {key}, 文件路径={file_path_obj}")

                                # 删除文件
                                if file_path_obj.exists() and file_path_obj.is_file():
                                    file_path_obj.unlink()
                                    logger.info(f"🗑️ 删除文件: {file_path_obj}")

                                    # 清理空目录（每次删除文件后立即执行）
                                    remove_empty_parents_safely(
                                        file_path=file_path_obj,
                                        stop_at=Path(FileConfig.TEMP_DIR).resolve(),
                                        max_retries=2
                                    )
                                else:
                                    logger.warning(f"文件不存在或非文件: {file_path_obj}")

                            # 删除 Redis 键
                            conn.delete(key)
                            deleted_count += 1
                            logger.info(f"✅ 清理完成: {key}")
                    except Exception as e:
                        logger.error(f"清理失败: {key} - {str(e)}", exc_info=True)

                if cursor == 0:  # 游标归零时退出
                    break

            logger.info(f"🎉 清理完成，共扫描 {total_scanned} 个键，删除 {deleted_count} 个过期文件")

    except Exception as e:
        logger.error("清理任务发生全局错误: %s", str(e), exc_info=True)
        raise self.retry(exc=e, countdown=300, max_retries=3)
