from agent.tools.extraction_tools import ocr_extract
import os

# 测试路径
current_dir = os.path.dirname(os.path.abspath(__file__))
pdf_files = [
    os.path.join(current_dir, "docs/test/发票.pdf"),
    os.path.join(current_dir, "docs/test/清华大学_26112000001297155376_20260402121025.pdf")
]

print("=== 详细测试 OCR 功能 ===")

for pdf_file in pdf_files:
    print(f"\n测试文件: {pdf_file}")
    print(f"文件存在: {os.path.exists(pdf_file)}")
    
    # 测试 ocr_extract 函数
    result = ocr_extract(pdf_file)
    print(f"成功: {result.success}")
    print(f"错误: {result.error}")
    print(f"数据: {result.data}")
    
    if result.data:
        text = result.data.get("text", "")
        print(f"提取文本: {text}")
