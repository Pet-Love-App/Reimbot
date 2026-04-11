from agent.tools.doc_tools import generate_word_doc, generate_excel_sheet

# 测试数据
activity = {
    "activity_content": "学生团建活动",
    "activity_location": "会议室A",
    "name": "张三",
    "participants": "10人",
    "contact": "13800138000",
    "activity_time": "2024-01-01",
    "expense_detail": "餐饮费用：500元\n场地费用：300元"
}

invoice = {
    "invoice_no": "123456",
    "amount": 800.0,
    "invoice_date": "2024-01-01",
    "content": "餐饮服务"
}

# 测试生成 Word 文档
print("=== 测试生成 Word 文档 ===")
word_result = generate_word_doc(activity, [invoice], template_name="学生活动经费使用情况.docx")
print(f"Word 生成结果: {word_result.success}")
if word_result.success:
    print(f"Word 文件路径: {word_result.data.get('word_path')}")
else:
    print(f"Word 生成失败: {word_result.error}")

# 测试生成 Excel 文档
print("\n=== 测试生成 Excel 文档 ===")
excel_result = generate_excel_sheet([invoice], activity, template_name="学生活动经费报销明细模板.xlsx")
print(f"Excel 生成结果: {excel_result.success}")
if excel_result.success:
    print(f"Excel 文件路径: {excel_result.data.get('excel_path')}")
else:
    print(f"Excel 生成失败: {excel_result.error}")
