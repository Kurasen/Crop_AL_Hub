FROM python:3.12-bullseye

# 创建标准目录
RUN mkdir -p /data/images /output

# 安装依赖（模拟真实环境）
RUN pip install --no-cache-dir numpy

# 模拟处理脚本
COPY fake_algorithm.py .

CMD ["python", "fake_algorithm.py"]
