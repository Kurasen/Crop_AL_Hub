import os
import redis
import time

# 初始化路径
test_dir = "/tmp/cleanup_test"
os.makedirs(test_dir, exist_ok=True)

# 创建真实测试文件
open(f"{test_dir}/expired.txt", "w").write("test")
open(f"{test_dir}/valid.txt", "w").write("test")

# 连接Redis
r = redis.Redis()

# 插入测试数据
test_data = [
    ("temp:test:expired", int(time.time())-10, f"{test_dir}/expired.txt"),
    ("temp:test:valid", int(time.time())+3600, f"{test_dir}/valid.txt"),
    ("temp:test:danger", int(time.time())-10, "/etc/passwd")
]

for key, expire, path in test_data:
    r.hmset(key, {
        "expire_at": expire,
        "real_path": path
    })
print("测试数据生成完成！")