from agent.tools.input_tools import scan_inputs
import os

# 测试路径
current_dir = os.path.dirname(os.path.abspath(__file__))
paths = [
    os.path.join(current_dir, "docs/test/发票.pdf"),
    os.path.join(current_dir, "docs/test/清华大学_26112000001297155376_20260402121025.pdf")
]

print("测试路径:", paths)
print("路径是否存在:")
for path in paths:
    print(f"{path}: {os.path.exists(path)}")

# 测试 scan_inputs 函数
result = scan_inputs(paths)
print("\nscan_inputs 结果:")
print(f"成功: {result.success}")
print(f"错误: {result.error}")
print(f"数据: {result.data}")
