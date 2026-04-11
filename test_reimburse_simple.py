from agent.graphs.subgraphs.reimburse import (
    reimburse_start_node,
    scan_file_node,
    classify_file_node,
    extract_node,
    invoice_extract_node,
    activity_parse_node,
    rule_check_node,
    collect_info_node,
    gen_doc_node,
    gen_mail_node,
    save_record_node,
    reimburse_fail_node,
    route_after_scan,
    route_after_extract,
    route_after_rule_check,
    route_after_collect_info
)
import os

# 测试繁体数字转换
from agent.tools.extraction_tools import traditional_to_arabic, extract_invoice_fields

def test_traditional_to_arabic():
    print("\n=== 测试繁体数字转换 ===")
    test_cases = [
        "壹仟壹佰玖拾陆圆壹角整",
        "壹仟壹佰玖拾陆元壹角整",
        "壹仟壹佰玖拾陆",
        "壹佰贰拾叁元肆角伍分",
        "伍拾陆元捌角",
        "叁元伍角",
        "壹元",
    ]
    
    for test_case in test_cases:
        try:
            result = traditional_to_arabic(test_case)
            print(f"{test_case} -> {result}")
        except Exception as e:
            print(f"{test_case} -> 错误: {e}")

def test_extract_invoice_fields():
    print("\n=== 测试发票信息提取 ===")
    # 使用用户提供的真实发票文本
    test_text = """项目名称 规格型号 单  位 数  量 单  价 金  额 税率/征收率 税  额 
 合 计 
 价税合计（大写） （小写） 
 备 
 注 
 开票人： 
 26112000001297155376 
 2026年04月02日 
 清华大学 
 12100000400000624D 
 北京吉野家快餐有限公司 
 911100006000650192 
 ¥1128.40 ¥67.70 
 壹仟壹佰玖拾陆圆壹角整 ¥1196.10 
 曲田田 
 曲田田 
 *餐饮服务*餐费 6%1128.40 67.701128.41"""
    
    try:
        result = extract_invoice_fields(test_text)
        if result.success:
            invoice = result.data.get("invoice", {})
            print(f"提取结果:")
            print(f"  发票编号: {invoice.get('invoice_no')}")
            print(f"  金额: {invoice.get('amount')}")
            print(f"  日期: {invoice.get('date')}")
            print(f"  内容: {invoice.get('content')}")
        else:
            print(f"提取失败: {result.message}")
    except Exception as e:
        print(f"提取错误: {e}")

# 测试数据
current_dir = os.path.dirname(os.path.abspath(__file__))

# 运行测试函数
test_traditional_to_arabic()
test_extract_invoice_fields()

# 使用用户提供的真实信息
state = {
    "payload": {
        "paths": [
            os.path.join(current_dir, "docs/test/发票.pdf"),
            os.path.join(current_dir, "docs/test/清华大学_26112000001297155376_20260402121025.pdf")
        ],
        "activity_text": "学生会午餐会活动，地点：学校食堂，时间：2026-04-11，参与人员：叶思萌、张奥淇",
        "output_dir": os.path.join(current_dir, "docs/test")
    },
    "task_progress": []
}

print("\n=== 简单测试 Reimburse 子图 ===")
print("步骤 1: 启动节点")
state = reimburse_start_node(state)

print("步骤 2: 扫描文件")
state = scan_file_node(state)

print("步骤 3: 路由 - 扫描后")
next_node = route_after_scan(state)
print(f"  目标节点: {next_node}")

if next_node == "ClassifyFileNode":
    print("步骤 4: 分类文件")
    state = classify_file_node(state)
    
    print("步骤 5: 提取文本")
    state = extract_node(state)
    
    print("步骤 6: 路由 - 提取后")
    next_node = route_after_extract(state)
    print(f"  目标节点: {next_node}")
    
    if next_node == "InvoiceExtractNode":
        print("步骤 7: 提取发票信息")
        state = invoice_extract_node(state)
        
    print("步骤 8: 解析活动信息")
    state = activity_parse_node(state)
    
    print("步骤 9: 规则校验")
    state = rule_check_node(state)
    
    print("步骤 10: 路由 - 规则校验后")
    next_node = route_after_rule_check(state)
    print(f"  目标节点: {next_node}")
    
    if next_node == "CollectInfoNode":
        print("步骤 11: 信息收集")
        state = collect_info_node(state)
        
        print("步骤 12: 路由 - 信息收集后")
        next_node = route_after_collect_info(state)
        print(f"  目标节点: {next_node}")
        
        # 模拟对话，填充缺失的字段
        if next_node == "AskUserNode":
            print("步骤 13: 模拟用户对话")
            # 填充缺失的字段
            missing_fields = state.get("missing_fields", [])
            if missing_fields:
                print(f"  缺失字段: {[field['label'] for field in missing_fields]}")
                # 模拟用户输入
                activity = state.get("activity", {})
                invoice = state.get("invoice", {})
                
                # 填充 activity 字段，使用用户提供的真实信息
                activity["student_name"] = "叶思萌"
                activity["contact"] = "13800138000"
                activity["participants"] = "叶思萌、张奥淇"
                activity["organization"] = "学生会"
                activity["student_id"] = "2023012164"
                activity["activity_date"] = "2026-04-11"
                activity["location"] = "学校食堂"
                
                # 只填充活动信息，不填充发票数据，使用从真实发票中提取的数据
                state["activity"] = activity
                
                # 打印从真实发票中提取的信息
                print(f"  从真实发票中提取的信息:")
                print(f"  发票数量: {len(state.get('invoices', []))}")
                print(f"  总金额: {state.get('total_amount', 0.0)}")
                for i, inv in enumerate(state.get('invoices', []), 1):
                    print(f"  发票 {i}: 编号={inv.get('invoice_no', '')}, 金额={inv.get('amount', 0)}, 日期={inv.get('date', '')}, 内容={inv.get('content', '')}")
                
                # 移除打印 OCR 原始文本的部分，避免 UnicodeEncodeError
                print("  已填充缺失字段")
        
        if next_node == "GenDocNode" or next_node == "AskUserNode":
            print("步骤 14: 生成文档")
            state = gen_doc_node(state)
            
            print("步骤 15: 生成邮件")
            state = gen_mail_node(state)
    
    print("步骤 16: 保存记录")
    state = save_record_node(state)

print("\n=== 测试完成 ===")
result = state.get("result", {})
print(f"最终结果 - 类型: {result.get('type')}")
print(f"最终结果 - 状态: {result.get('status', 'success')}")
print(f"最终结果 - 记录ID: {result.get('record_id')}")
print(f"最终结果 - 错误: {len(result.get('errors', []))}")

if result.get('outputs'):
    print("\n生成的文件:")
    for key, value in result.get('outputs', {}).items():
        if value:
            print(f"  {key}: {value}")
