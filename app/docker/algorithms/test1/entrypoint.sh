#!/bin/sh

echo "=== 输入目录结构验证 ==="
echo "绝对路径: $(realpath /data/images)"
echo "内容列表:"
ls -lR /data/images  # 用ls替代tree

echo "=== 开始复制 ==="
cp -rv /data/images/. /output/  # 修正复制路径

echo "=== 输出验证 ==="
ls -lR /output
