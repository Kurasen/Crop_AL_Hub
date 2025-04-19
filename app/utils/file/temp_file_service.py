import gc
import hashlib
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from celery.exceptions import Reject
from redis.exceptions import LockNotOwnedError, LockError

from app.config import FileConfig
from app.core.exception import ValidationError, logger, FileUploadError, RedisConnectionError, FileSaveError, \
    NotFoundError, FileCleanupError
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
    # if not file_path.is_relative_to(Path(FileConfig.TEMP_DIR).resolve()):
    #     logger.warning(f"⚠️ 拒绝处理非临时目录: {file_path}")
    #     return

    logger.info("file_path: %s, stop_at: %s", file_path, stop_at)

    current_dir = file_path.parent

    while current_dir != stop_at and current_dir.is_relative_to(stop_at):
        logger.debug("▶ 开始处理目录: %s", current_dir)

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

    @staticmethod
    def cleanup_temp_files(src_file: Path, is_temp: bool = True):
        """原子化清理临时文件"""
        try:
            if src_file.exists():
                src_file.unlink(missing_ok=True)
                # 根据文件类型设置 stop_at
                stop_at = (
                    Path(FileConfig.TEMP_DIR).resolve()
                    if is_temp
                    else Path(FileConfig.FORMAL_RIR).resolve()
                )
                remove_empty_parents_safely(
                    file_path=src_file,
                    stop_at=stop_at,
                    max_retries=3
                )
        except Exception as e:
            logger.error(f"文件清理失败: {e}")
            raise FileCleanupError("文件清理失败")  # 自定义异常

    @staticmethod
    def _update_redis_status(redis_key: str, error: Exception = None):
        """更新Redis状态"""
        try:
            with redis_pool.get_redis_connection('files') as conn:
                if isinstance(error, FileNotFoundError):
                    conn.delete(redis_key)
                elif error:
                    conn.hset(redis_key, "status", "error")
                else:
                    conn.delete(redis_key)
        except Exception as e:
            logger.error(f"Redis状态更新失败: {e}")

    def save_temp(self, file, upload_type: str, data_id: int, file_type: str, user_id: int) -> str:
        """保存到临时目录并生成URL"""
        try:
            # 生成文件哈希（使用文件内容）
            logger.info(f"upload_type: {upload_type}, file_type: {file_type}, data_id: {data_id}, file: {file}")

            # ========== 文件内容处理 ==========
            try:
                file_content = file.read()
                file_hash = hashlib.md5(file_content).hexdigest()
                file.seek(0)  # 重置文件指针
            except IOError as e:
                logger.error("文件读取失败: %s", e)
                raise FileUploadError("文件损坏或无法读取")

            logger.info(f"✅ 计算的文件哈希: {file_hash}")
            logger.info(f"✅ 保存的文件名: {file_hash}{Path(file.filename).suffix}")

            # ========== Redis重复检查 ==========
            version = datetime.now().strftime("%Y%m%d%H%M%S")
            redis_key = f"temp:{user_id}:{upload_type}:{data_id}:{file_type}:{version}:{file_hash}"
            try:
                with self.redis.get_redis_connection('files') as conn:
                    if conn.exists(redis_key):
                        current_status = conn.hget(redis_key, "status")
                        if current_status:
                            if current_status in ['pending', 'processing']:
                                raise FileUploadError("文件已上传，请勿重复提交")
            except RedisConnectionError as e:
                logger.error("Redis连接异常: %s", e)
                raise FileUploadError("系统繁忙，请稍后再试")

            # ========== 临时目录构建 ==========
            try:
                temp_dir = Path(FileConfig.TEMP_DIR) / FileConfig.UPLOAD_CONFIG[upload_type]['subdirectory'].format(
                    file_type=file_type,
                    data_id=data_id,
                    user_id=user_id,
                    version=version
                )
            except KeyError:
                logger.error("无效的上传类型: %s", upload_type)
                raise FileUploadError("不支持的上传类型")

            # 保存到临时目录
            # ========== 文件存储 ==========
            try:
                saved_path = self.storage.save_upload(
                    file_stream=file,
                    save_dir=temp_dir,
                    file_name=f"{file_hash}{Path(file.filename).suffix}"
                )
                saved_file_path = Path(saved_path) / f"{file_hash}{Path(file.filename).suffix}"
            except FileSaveError as e:
                logger.error("文件存储失败: %s", e)
                raise FileUploadError("文件保存失败")
            logger.info(f"临时保存目录: {saved_path}")
            logger.info(f"✅ 完整文件路径: {saved_file_path}")

            # ========== Redis记录 ==========
            try:
                with self.redis.get_redis_connection('files') as conn:
                    conn.hmset(redis_key, {
                        "real_path": str(saved_file_path),
                        "user_id": user_id,
                        "status": "pending",
                        "expire_at": int(time.time() + 10)
                    })
                    # conn.expire(key, 120)  # 原为7天（604800秒）
            except Exception as e:
                logger.error("Redis记录失败: %s", e)
                # 回滚已保存文件
                try:
                    saved_file_path.unlink(missing_ok=True)
                    remove_empty_parents_safely(saved_file_path, Path(FileConfig.TEMP_DIR))
                except Exception as cleanup_err:
                    logger.error("文件回滚失败: %s", cleanup_err)
                raise FileUploadError("系统临时错误")

            logger.info(f"✅ 保存到Redis的键: {redis_key}")
            logger.info(f"✅ 文件哈希: {file_hash}")
            logger.info(f"✅ 保存路径: {saved_path}")

            # 获取相对于 TEMP_DIR 的路径
            relative_path = Path(saved_path).relative_to(FileConfig.TEMP_DIR)

            # 生成URL路径（使用实际存储路径结构）
            url_path = f"{FileConfig.TEMP_BASE_URL}/{relative_path}/{file_hash}{Path(file.filename).suffix}"
            logger.info(f"✅ 生成的URL相对路径: {url_path}")

            return url_path
        except FileUploadError:
            raise
        except Exception as e:
            logger.error("未知异常", exc_info=True)
            raise FileUploadError("上传服务异常")  # 兜底异常处理

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
                user_id=user_id,
                version=url_components['version']
            )
            logger.info(f"✅ 解析得到的参数: {url_components}")
            logger.info(f"✅ 生成的Redis键: {redis_key}")

            return True
        except ValidationError as e:
            logger.error("文件验证失败：%s", str(e))
            raise e
        except Exception as e:
            logger.error("提交文件时发生未捕获的异常: %s", str(e))
            raise e

    @staticmethod
    @CeleryManager.get_celery().task(bind=True, expires=86400)
    def _move_to_final(self, redis_key: str, src_path: str, upload_type: str, data_id: int, file_type: str,
                       user_id: int, version: str) -> None:
        """原子化文件转移操作（增强健壮性）"""
        src_file = Path(src_path)
        final_file_path = None
        error = None

        try:
            src_file = Path(src_path)
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
                user_id=user_id,
                version=version
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

            # ========== 4. 数据库更新 ==========
            relative_path = str(final_file_path.relative_to(FileConfig.LOCAL_FILE_BASE))
            logger.info("新文件存放相对路径: %s", relative_path)

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
                db_committed = False
                try:
                    # 更新数据库
                    if upload_type in database_mapping and file_type in database_mapping[upload_type]:
                        get_func, field = database_mapping[upload_type][file_type]
                        instance = get_func(data_id)

                        old_relative_path = getattr(instance, field)
                        logger.info("旧文件存放相对路径：%s", old_relative_path)

                        # 更新数据库
                        setattr(instance, field, relative_path)
                        db.session.commit()
                        db_committed = True

                        # 获取旧路径并删除对应的文件
                        if file_type in FileConfig.SINGLE_FILE_TYPES:
                            if old_relative_path:
                                old_file = Path(FileConfig.LOCAL_FILE_BASE) / old_relative_path
                                if old_file.exists():
                                    try:
                                        TempFileService.cleanup_temp_files(old_file, is_temp=False)
                                        logger.info("🗑️ 删除旧文件: %s", old_file)
                                    except Exception as e:
                                        logger.error("⛔ 旧文件删除失败: %s", str(e))

                except Exception as e:
                    error = e
                    db.session.rollback()
                    logger.error("⛔ 数据库更新失败: %s", str(e))

            TempFileService._update_redis_status(redis_key)

        except FileNotFoundError as e:
            error = e
            # 6. 文件不存在时的专用处理
            logger.error(f"🛑 文件已删除，终止任务: {src_path}")
            with redis_pool.get_redis_connection('files') as conn:
                conn.delete(redis_key)  # 确保清理残留
            return  # 直接返回，不重试
        except Exception as e:
            error = e
            # 7. 其他错误处理
            logger.error(f"迁移失败: {str(e)}")
            with redis_pool.get_redis_connection('files') as conn:
                conn.hset(redis_key, "status", "error")
            raise self.retry(exc=e, countdown=60, max_retries=2)  # 有限重试
        finally:
            # ========== 确保最终清理 ==========
            # 无论成功与否，都尝试清理临时文件及目录
            TempFileService.cleanup_temp_files(src_file, is_temp=True)

            # 如果新文件已创建并未提交到数据库中且任务失败，清理新文件
            if error and final_file_path and final_file_path.exists() and not db_committed:
                try:
                    logger.info("回滚删除新文件: %s", final_file_path)
                    TempFileService.cleanup_temp_files(final_file_path, is_temp=False)
                except Exception as e:
                    logger.error("新文件清理失败: %s", str(e))


temp_service = TempFileService()


#
# @CeleryManager.get_celery().task(bind=True, expires=86400)
# def cleanup_temp_files(self):
#     logger.info("🚀 开始执行临时文件清理任务")
#     try:
#         with redis_pool.get_redis_connection('files') as conn:
#             cursor = '0'
#             deleted_count = 0
#             total_scanned = 0  # 统计扫描的键数量
#             while True:
#                 cursor, keys = conn.scan(cursor, match='temp:*', count=500)
#                 logger.info(f"🔍 扫描到 {len(keys)} 个键，cursor={cursor}")  # 新增日志
#                 total_scanned += len(keys)
#                 if not keys and cursor == 0:  # 退出条件：无键且游标归零
#                     break
#
#                 for key in keys:
#                     try:
#                         # 确保每次循环都初始化变量
#                         file_path_str = None
#                         file_path_obj = None
#
#                         fields = conn.hmget(key, ['expire_at', 'real_path'])
#                         expire_at, file_path_str = fields[0], fields[1]
#                         logger.debug(f"检查键: {key}, expire_at={expire_at}")
#                         # 条件判断和路径转换
#                         if expire_at and float(expire_at) < time.time():
#                             if file_path_str:
#                                 file_path_obj = Path(file_path_str)
#                                 logger.debug(f"处理过期键: {key}, 文件路径={file_path_obj}")
#
#                                 # 删除文件
#                                 if file_path_obj.exists() and file_path_obj.is_file():
#                                     file_path_obj.unlink()
#                                     logger.info(f"🗑️ 删除文件: {file_path_obj}")
#
#                                     # 清理空目录（每次删除文件后立即执行）
#                                     remove_empty_parents_safely(
#                                         file_path=file_path_obj,
#                                         stop_at=Path(FileConfig.TEMP_DIR).resolve(),
#                                         max_retries=2
#                                     )
#                                 else:
#                                     logger.warning(f"文件不存在或非文件: {file_path_obj}")
#
#                             # 删除 Redis 键
#                             conn.delete(key)
#                             deleted_count += 1
#                             logger.info(f"✅ 清理完成: {key}")
#
#                     except Exception as e:
#                         logger.error(f"清理失败: {key} - {str(e)}", exc_info=True)
#
#                 if cursor == 0:  # 游标归零时退出
#                     break
#
#             logger.info(f"🎉 清理完成，共扫描 {total_scanned} 个键，删除 {deleted_count} 个过期文件")
#
#     except Exception as e:
#         logger.error("清理任务发生全局错误: %s", str(e), exc_info=True)
#         raise self.retry(exc=e, countdown=300, max_retries=3)

@CeleryManager.get_celery().task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=30,
    time_limit=300,  # 5分钟超时
    soft_time_limit=280
)
def cleanup_temp_files(self):
    lock_key = "cleanup_temp_files_lock"
    max_memory = 512 * 1024 * 1024  # 512MB更安全

    try:
        with redis_pool.get_redis_connection('files') as conn:
            # 使用统一连接创建锁对象
            lock = conn.lock(
                name=lock_key,
                timeout=300,  # 与任务超时对齐
                blocking_timeout=15,
                thread_local=False
            )

            # 原子化锁操作
            if not lock.acquire(blocking=False):
                current_owner = conn.get(f"{lock_key}:holder")
                logger.warning(f"⏳ 清理任务进行中 | 持有者: {safe_redis_decode(current_owner)}")
                raise Reject("已有运行中的清理任务", requeue=False)

            try:
                # 记录锁持有者
                conn.setex(f"{lock_key}:holder", 300, f"Task:{self.request.id}")
                logger.info(f"🔒 锁获取成功 | 任务ID: {self.request.id}")
                logger.info("★ 进入核心清理流程")

                # 核心清理逻辑(保持原处理流程)
                result = execute_cleanup_process(conn, max_memory)
                logger.info(f"★ 清理完成，共删除 {result} 个Redis键")  # 新增
                return result

            finally:
                try:
                    lock.release()
                    conn.delete(f"{lock_key}:holder")
                    logger.info("🔓 锁已释放")
                except LockNotOwnedError:
                    logger.warning("⚠️ 锁已自动过期")

    except (LockError, ConnectionError) as e:
        logger.error("🔑 锁操作异常: %s", str(e))
        raise self.retry(exc=e, countdown=60)
    finally:
        gc.collect()


def execute_cleanup_process(conn, max_memory):
    """完整的清理流程实现（带内存/超时保护）"""
    deleted_count = 0  # 实际已删除的Redis键计数
    expired_data_buffer = []  # # 存储待删除的 (key, path) 元组
    batch_size = 200
    start_time = time.time()
    last_log_time = start_time

    try:
        # ====== 诊断日志 ======
        logger.info(f"★ 当前Redis配置: {conn.connection_pool.connection_kwargs}")

        # ====== 1. 初始化扫描 ======
        cursor = 0
        total_scanned = 0
        logger.info("★ 开始扫描Redis临时键")

        # 内存保护检查点
        def memory_guard():
            current_mem = psutil.Process().memory_info().rss
            if current_mem > max_memory:
                logger.error(f"🛑 内存超限: {current_mem // 1024 // 1024}MB > {max_memory // 1024 // 1024}MB")
                raise MemoryError("内存超限保护触发")

        # ====== 2. 主扫描循环 ======
        logger.info("cursor为：%s", cursor)
        while True:
            # 检查内存状态（每次循环前）
            memory_guard()

            # 周期性日志（每30s）
            if time.time() - last_log_time > 30:
                logger.info(
                    f"⏱️ 已运行: {int(time.time() - start_time)}秒 | "
                    f"扫描键: {total_scanned} | 清理文件: {deleted_count}"
                )
                last_log_time = time.time()

            # ====== 2.1 分批次SCAN ======
            next_cursor, keys = conn.scan(
                cursor=cursor,
                match='temp:*',  # 限定键名前缀
                count=batch_size  # 每批数量
            )
            cursor = int(next_cursor)  # 转换为整数
            logger.info(f"★ 扫描到 {len(keys)} 个键 | 新游标: {cursor}")  # 新增

            total_scanned += len(keys)
            if not keys and cursor == 0:  # 退出条件：无键且游标归零
                break

            # ====== 2.2 批量获取过期时间 ======
            # 使用pipeline减少网络开销
            with conn.pipeline() as pipe:
                for key in keys:
                    pipe.hget(key, 'expire_at')  # 获取过期时间字段
                expire_timestamps = pipe.execute()

            # ====== 2.3 过滤过期键 ======
            current_time = time.time()
            expired_keys = []
            for key, expire_at in zip(keys, expire_timestamps):
                if not expire_at:
                    continue
                try:
                    if float(expire_at) < current_time:
                        expired_keys.append(key)
                except (TypeError, ValueError):
                    logger.warning(f"⏳ 无效过期时间: key={key}, value={expire_at}")

            logger.info(f"★ 发现 {len(expired_keys)} 个过期键")

            # ====== 2.4 批量获取文件路径 ======
            if expired_keys:
                with conn.pipeline() as pipe:
                    for key in expired_keys:
                        pipe.hget(key, 'real_path')
                    real_paths = pipe.execute()

                # 过滤有效路径 构建 (key, path)对
                valid_pairs = []
                for key, path in zip(expired_keys, real_paths):
                    if path and is_safe_path(path, log_errors=False):
                        valid_pairs.append((key, path))
                    else:
                        logger.warning(f"⏳ 忽略无效路径: key={key}, path={path}")

                # 添加到缓冲区（不再立即删除键）
                expired_data_buffer.extend(valid_pairs)
                logger.info(f"★ 新增待清理项: {len(valid_pairs)}")

                # ====== 2.5 触发异步清理（关键修改点）=====
                if len(expired_data_buffer) >= 300:  # 每300条提交一次
                    # 提交文件删除任务
                    file_paths = [path for _, path in expired_data_buffer]
                    safe_async_clean(file_paths)

                    # 删除Redis键（仅在任务提交后执行）
                    keys_to_delete = [key for key, _ in expired_data_buffer]
                    for chunk in chunks(keys_to_delete, 100):
                        deleted = conn.delete(*chunk)
                        deleted_count += deleted
                        logger.info(f"🔑 删除Redis键批次: 提交{len(chunk)} → 实际删除{deleted}")

                    # 清空缓冲区
                    expired_data_buffer.clear()

            # ====== 2.7 超时保护 ======
            if time.time() - start_time > 250:  # 预留50秒缓冲
                logger.warning("⏳ 接近超时，终止扫描")
                break

            if cursor == 0:
                logger.info("★ SCAN游标归零，结束扫描")
                break  # 关键修正：无论是否有键都退出循环

        # ====== 3. 最终清理 ======
        if expired_data_buffer:
            # 提交剩余文件删除任务
            file_paths = [path for _, path in expired_data_buffer]
            safe_async_clean(file_paths)

            # 删除剩余Redis键
            keys_to_delete = [key for key, _ in expired_data_buffer]
            deleted = conn.delete(*keys_to_delete)
            deleted_count += deleted
            logger.info(f"🚮 最终提交: 删除{deleted}个键及文件")

        logger.info(f"★ 主扫描循环结束 | 总扫描 {total_scanned} 键 | 实际删除 {deleted_count} 键")

        # 新增部分 - 使用Redis记录扫描次数
        scan_flag_key = "temp_cleanup:dir_scan_flag"
        try:
            scan_counter = int(conn.incr(scan_flag_key))
            logger.info(f"当前扫描计数器: {scan_counter}")
            conn.expire(scan_flag_key, 86400)  # 24小时过期
            if scan_counter % 3 == 0:  # 每3次执行触发一次
                scan_orphaned_files()
                conn.delete(scan_flag_key)  # 重置计数器
        except Exception as e:
            logger.error(f"目录扫描计数器异常: {str(e)}")

        return deleted_count

    except MemoryError:
        logger.critical("🛑 内存保护触发，紧急释放资源")
        if expired_data_buffer:
            file_paths = [path for _, path in expired_data_buffer]
            safe_async_clean(file_paths)
        raise
    except Exception as e:
        logger.error(f"‼️ 清理异常: {str(e)}", exc_info=True)
        raise


def safe_async_clean(file_paths):
    """直接处理文件路径的异步清理"""
    try:
        # 分批次处理防止内存溢出
        for i in range(0, len(file_paths), 100):
            batch = file_paths[i:i + 100]

            # 过滤安全路径
            safe_paths = [p for p in batch if is_safe_path(p, log_errors=False)]
            if not safe_paths:
                continue

            # 分块提交任务（每块10个路径）
            for path_chunk in chunks(safe_paths, 10):
                async_delete_file.chunks(
                    [(path,) for path in path_chunk], 10  # ✅ 注意这里使用列表推导式生成参数元组
                ).apply_async(
                    queue='cleanup_low',
                    priority=9
                )

    except Exception as e:
        logger.error("文件清理管道错误: %s", str(e))


@CeleryManager.get_celery().task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=30,
    time_limit=120
)
def async_delete_file(self, path):
    """异步安全删除"""
    logger.info(f"📤 接收到删除任务: {path}")
    try:

        if not is_safe_path(path):
            logger.error(f"非法路径拒绝操作: {path}")
            return

        file_path = Path(path)
        if not file_path.exists():
            logger.error(f"文件不存在: {path}")
            return

        # 目录清理（带重试机制）
        for attempt in range(3):
            try:
                file_path.unlink(missing_ok=True)
                logger.info(f"🗑️ 文件删除成功: {path}")
                # 目录清理（带父级校验）
                remove_empty_parents_safely(
                    file_path=file_path,
                    stop_at=Path(FileConfig.TEMP_DIR).resolve(),
                    max_retries=2
                )
                break
            except PermissionError:
                if attempt == 2:
                    logger.error(f"权限不足: {path}")
                    raise
                time.sleep(1)
            except FileNotFoundError:
                break
            except Exception as e:
                logger.warning(f"删除异常[{attempt + 1}/3]: {path} - {str(e)}")
                time.sleep(0.5)

    except Exception as e:
        logger.error(f"🗑️ 文件删除失败（{self.retries}/2次重试）: {path}", exc_info=True)
        raise self.retry(exc=e, countdown=30)
    finally:
        # 强制释放资源
        del file_path
        gc.collect()


def is_safe_path(path, log_errors=True):
    """路径安全检查"""
    try:
        resolved = Path(path).resolve()
        temp_base = Path(FileConfig.TEMP_DIR).resolve()
        safe = temp_base in resolved.parents
        if not safe and log_errors:
            logger.warning(f"路径不安全: {path} -> {resolved}")
        return safe
    except Exception as e:
        if log_errors:
            logger.debug(f"路径解析异常: {path} - {str(e)}")
        return False


def chunks(items, chunk_size):
    """带空值过滤的分块函数"""
    return (items[i:i + chunk_size] for i in range(0, len(items), chunk_size))


def safe_redis_decode(data):
    """安全解码Redis返回值"""
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='replace')
    return str(data) if data is not None else ""


def scan_orphaned_files():
    """兜底扫描暂存目录（安全遍历版本）"""
    logger.info("🏁 开始执行兜底目录扫描...")
    temp_dir = Path(FileConfig.TEMP_DIR).resolve()
    count = 0
    total_files = 0

    # 安全收集所有文件路径
    file_paths = []
    try:
        for entry in temp_dir.rglob('*'):
            try:
                if entry.is_file():
                    file_paths.append(entry)
            except FileNotFoundError:
                logger.debug("路径在扫描时已被删除: %s", entry)
    except FileNotFoundError as e:
        logger.warning("基础目录不存在: %s", str(e))
        return 0

    # 处理收集到的文件
    for file_path in file_paths:
        try:
            # 二次检查文件状态（可能在收集后被其他进程删除）
            if not file_path.exists():
                logger.debug("文件已不存在，跳过: %s", file_path)
                continue

            total_files += 1
            logger.debug("扫描到文件: %s", file_path)

            # 安全检查路径有效性
            if not is_safe_path(str(file_path)):
                logger.warning("检测到不安全路径，跳过: %s", file_path)
                continue

            # 检查目录过期状态
            dir_expired = False
            current_dir = file_path.parent

            while current_dir != temp_dir:
                # 安全解析路径避免符号链接问题
                current_dir = current_dir.resolve()
                dir_name = current_dir.name

                # 检测时间戳目录格式
                if len(dir_name) == 14 and dir_name.isdigit():
                    try:
                        dir_time = datetime.strptime(dir_name, "%Y%m%d%H%M%S").timestamp()
                        if time.time() - dir_time > FileConfig.TEMP_FILE_MAX_AGE:
                            dir_expired = True
                            break
                    except ValueError:
                        pass  # 非时间戳目录跳过

                # 向上遍历时确保路径有效
                if not current_dir.exists():
                    logger.debug("父目录已被删除，停止向上检查: %s", current_dir)
                    break
                current_dir = current_dir.parent

            if dir_expired:
                try:
                    TempFileService.cleanup_temp_files(file_path)
                    count += 1
                except Exception as e:
                    logger.error("目录过期文件删除失败 %s: %s", file_path, str(e))
                continue

            # 最后修改时间检查
            try:
                file_mtime = file_path.stat().st_mtime
                if file_mtime < (time.time() - FileConfig.TEMP_FILE_MAX_AGE):
                    TempFileService.cleanup_temp_files(file_path)
                    count += 1
            except FileNotFoundError:
                logger.debug("文件已被删除，跳过: %s", file_path)
            except Exception as e:
                logger.error("mtime检查失败 %s: %s", file_path, str(e))

        except FileNotFoundError:
            logger.debug("文件处理时已被删除，跳过: %s", file_path)
        except Exception as e:
            logger.error("文件处理异常 %s: %s", file_path, str(e), exc_info=True)

    logger.info("📊 共扫描到孤儿文件: %d | 已清理数量: %d", total_files, count)
    return count