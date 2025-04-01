# 文件复制专用Dockerfile
FROM alpine:3.16

# 安装必要工具
RUN apk add --no-cache coreutils

# 创建目录结构
RUN mkdir -p /data/images /output

# 设置启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
