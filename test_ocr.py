from agent.tools.extraction_tools import extract_text_from_files
import os

# 测试路径
current_dir = os.path.dirname(os.path.abspath(__file__))
files = {
    "pdf": [
        os.path.join(current_dir, "docs/test/发票.pdf"),
        os.path.join(current_dir, "docs/test/清华大学_26112000001297155376_20260402121025.pdf")
    ],
    "image": [],
    "word": [],
    "excel": [],
    "text": [],
    "other": []
}

print("=== 测试 OCR 功能 ===")
print("测试文件:", files)

# 测试 extract_text_from_files 函数
result = extract_text_from_files(files)
print("\nextract_text_from_files 结果:")
print(f"成功: {result.success}")
print(f"错误: {result.error}")
print(f"数据: {result.data}")

# 查看合并文本
if result.success:
    merged_text = result.data.get("merged_text", "")
    print("\n合并文本:", merged_text)
    
    # 检查是否有 OCR 错误
    if "OCR ERROR" in merged_text:
        print("\n❌ OCR 服务连接失败")
    else:
        print("\n✅ OCR 服务正常")
