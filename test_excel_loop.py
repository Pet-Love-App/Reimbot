from agent.tools.doc_tools import generate_excel_sheet

# 测试数据
activity = {
    "activity_name": "学生团建活动",
    "activity_date": "2024-01-01",
    "org": "学生会",
    "student_name": "张三",
    "student_id": "20210001"
}

# 多个发票数据
invoices = [
    {
        "invoice_no": "123456",
        "amount": 500.0,
        "invoice_date": "2024-01-01",
        "content": "餐饮费用"
    },
    {
        "invoice_no": "789012",
        "amount": 300.0,
        "invoice_date": "2024-01-02",
        "content": "场地费用"
    },
    {
        "invoice_no": "345678",
        "amount": 200.0,
        "invoice_date": "2024-01-03",
        "content": "物资费用"
    }
]

# 测试生成 Excel 文档
print("=== 测试生成 Excel 文档（带循环）===")
excel_result = generate_excel_sheet(invoices, activity, template_name="学生活动经费报销明细模板.xlsx")
print(f"Excel 生成结果: {excel_result.success}")
if excel_result.success:
    print(f"Excel 文件路径: {excel_result.data.get('excel_path')}")
else:
    print(f"Excel 生成失败: {excel_result.error}")
