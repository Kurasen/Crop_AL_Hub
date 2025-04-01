import os
import time
from pathlib import Path

input_dir = Path("/data/images")
output_dir = Path("/output")

# 模拟处理时间
time.sleep(10)

# 生成假输出
(output_dir / "result.txt").write_text(
    f"Processed {len(list(input_dir.glob('*')))} files"
)
