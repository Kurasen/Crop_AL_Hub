FROM python:3.12-bullseye

# 升级 pip 到最新版本
RUN python -m pip install --upgrade pip
# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 和安装依赖
COPY requirements.txt /app/
RUN pip install --progress-bar off -r requirements.txt

# 复制整个应用程序到容器中
COPY . /app/

# 设置环境变量
ENV FLASK_APP=app:create_app
ENV FLASK_RUN_HOST=0.0.0.0

# 启动 Flask 应用
#CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

#CMD ["tail", "-f", "/dev/null"]

CMD ["python", "myapp.py"]