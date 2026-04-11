from agent.tools.extraction_tools import ocr_extract
import os

# 测试路径
current_dir = os.path.dirname(os.path.abspath(__file__))
pdf_file = os.path.join(current_dir, "docs/test/发票.pdf")

print("=== 简单测试 OCR 功能 ===")
print(f"测试文件: {pdf_file}")
print(f"文件存在: {os.path.exists(pdf_file)}")

# 测试 ocr_extract 函数
result = ocr_extract(pdf_file)
print(f"成功: {result.success}")
print(f"错误: {result.error}")

if result.success:
    text = result.data.get("text", "")
    print(f"提取文本长度: {len(text)}")
    print("OCR 成功！")
else:
    print("OCR 失败！")
