from agent.graphs.subgraphs.reimburse import (
    reimburse_start_node,
    scan_file_node,
    classify_file_node,
    extract_node,
    invoice_extract_node,
    activity_parse_node,
    rule_check_node,
    gen_doc_node,
    gen_mail_node,
    save_record_node,
    reimburse_fail_node,
    route_after_scan,
    route_after_extract,
    route_after_rule_check
)

import os

# 测试数据
current_dir = os.path.dirname(os.path.abspath(__file__))
state = {
    "payload": {
        "paths": [
            os.path.join(current_dir, "docs/test/发票.pdf"),
            os.path.join(current_dir, "docs/test/清华大学_26112000001297155376_20260402121025.pdf")
        ],
        "activity_text": "学生团建活动，地点：会议室A，时间：2024-01-01，参与人员：10人",
        "output_dir": os.path.join(current_dir, "docs/parsed/reimburse_outputs")
    },
    "task_progress": []
}

print("=== 测试 Reimburse 子图 ===")
print("初始状态:", state)

# 1. 启动节点
state = reimburse_start_node(state)
print("\n1. 启动节点后:", state)

# 2. 扫描文件
state = scan_file_node(state)
print("\n2. 扫描文件后:", state)

# 3. 路由：扫描后
next_node = route_after_scan(state)
print(f"\n3. 扫描后路由: {next_node}")

if next_node == "ClassifyFileNode":
    # 4. 分类文件
    state = classify_file_node(state)
    print("\n4. 分类文件后:", state)
    
    # 5. 提取文本
    state = extract_node(state)
    print("\n5. 提取文本后:", state)
    
    # 6. 路由：提取后
    next_node = route_after_extract(state)
    print(f"\n6. 提取后路由: {next_node}")
    
    if next_node == "InvoiceExtractNode":
        # 7. 提取发票信息
        state = invoice_extract_node(state)
        print("\n7. 提取发票信息后:", state)
    
    # 8. 解析活动信息
    state = activity_parse_node(state)
    print("\n8. 解析活动信息后:", state)
    
    # 9. 规则校验
    state = rule_check_node(state)
    print("\n9. 规则校验后:", state)
    
    # 10. 路由：规则校验后
    next_node = route_after_rule_check(state)
    print(f"\n10. 规则校验后路由: {next_node}")
    
    if next_node == "GenDocNode":
        # 11. 生成文档
        state = gen_doc_node(state)
        print("\n11. 生成文档后:", state)
        
        # 12. 生成邮件
        state = gen_mail_node(state)
        print("\n12. 生成邮件后:", state)
    
    # 13. 保存记录
    state = save_record_node(state)
    print("\n13. 保存记录后:", state)

print("\n=== 测试完成 ===")
print("最终结果:", state.get("result", {}))
