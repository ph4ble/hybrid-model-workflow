"""
HAL 混合模型工作流实现
任务路由决策、执行层调用、强模型验收
"""

import json
import re
from typing import Dict, List, Optional, Tuple, Any

class HybridModelWorkflow:
    """混合模型工作流管理器"""
    
    def __init__(self, config_path="~/.hermes/config.yaml"):
        self.config_path = config_path
        self.cheap_model = "DeepSeek-V3.1"
        self.strong_model = "claude-opus-4-6"
        
        # 任务分类阈值
        self.simple_char_threshold = 160
        self.simple_word_threshold = 28
        
        # 高风险关键词（扩展版）
        self.high_risk_keywords = [
            # 决策判断类
            "建议", "推荐", "决定", "选择", "应该", "最好", "最优", 
            "判断", "评估", "分析", "策略", "规划", "架构", "设计",
            # 创作编写类
            "写", "编写", "生成", "创造", "创建", "制作", "编程", 
            "代码", "脚本", "开发", "构建", "实现", "撰写", "起草",
            # 策略规划类
            "策划", "方案", "计划", "安排", "筹备", "部署", "执行",
            # 复杂分析类
            "解析", "解释", "理解", "洞察", "探索", "研究", "调查"
        ]
        
        # 执行层任务类型
        self.execution_task_types = [
            "检索", "搜索", "查找", "提取", "清洗", "清理", "整理", 
            "格式化", "转换", "汇总", "摘要", "总结", "分类", "归纳"
        ]
        
    def analyze_task(self, user_message: str) -> Dict[str, Any]:
        """分析任务，返回路由决策"""
        
        # 基础统计
        char_count = len(user_message)
        word_count = len(user_message.split())
        
        # 判断清晰度
        clarity_score = self._calculate_clarity(user_message)
        
        # 判断风险等级
        risk_score = self._calculate_risk(user_message)
        
        # 判断可拆解性
        decomposability_score = self._calculate_decomposability(user_message)
        
        # 判断是否直接交付
        requires_direct_delivery = self._requires_direct_delivery(user_message)
        
        return {
            "task_analysis": {
                "char_count": char_count,
                "word_count": word_count,
                "clarity": clarity_score,
                "risk_score": risk_score,
                "decomposability_score": decomposability_score,
                "requires_direct_delivery": requires_direct_delivery
            },
            "routing_decision": self._make_routing_decision(
                char_count, word_count, clarity_score, 
                risk_score, decomposability_score, requires_direct_delivery
            )
        }
    
    def _calculate_clarity(self, message: str) -> float:
        """计算任务清晰度分数 (0-1)"""
        score = 0.5  # 基础分数
        
        # 检查明确目标
        if re.search(r'(帮我|请|想要|需要).*(一下|处理|解决|做)', message):
            score += 0.1
        
        # 检查具体对象
        if re.search(r'(文件|文档|数据|信息|代码|文本|单词|词汇)', message):
            score += 0.1
        
        # 检查明确动作
        if re.search(r'(找到|提取|整理|汇总|翻译|分析|解释|检查|修复)', message):
            score += 0.1
        
        # 检查具体输出格式
        if re.search(r'(列表|表格|JSON|CSV|MD|Markdown|格式)', message):
            score += 0.1
        
        # 检查问题是否完整
        if message.strip().endswith('?') or message.strip().endswith('？'):
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_risk(self, message: str) -> float:
        """计算风险分数 (0-1)"""
        score = 0.0
        
        message_lower = message.lower()
        
        # 检查高风险关键词
        for keyword in self.high_risk_keywords:
            if keyword.lower() in message_lower:
                score += 0.1
        
        # 检查是否有判断性质的内容
        if re.search(r'(哪个|哪项|哪个好|更好|更优|比较)', message_lower):
            score += 0.2
        
        # 检查是否有策略/建议要求
        if re.search(r'(策略|方法|方案|建议|推荐)', message_lower):
            score += 0.2
        
        # 检查是否有决策要求
        if re.search(r'(决定|选择|取舍|优先级)', message_lower):
            score += 0.2
        
        # 检查是否有重大影响
        if re.search(r'(重要|关键|核心|主要|重大)', message_lower):
            score += 0.2
        
        # 检查编程相关任务（高风险）
        if re.search(r'(写.*脚本|编写.*代码|创建.*程序|开发.*应用|实现.*算法)', message_lower):
            score += 0.3
        
        # 检查设计规划类任务（高风险）
        if re.search(r'(设计.*计划|规划.*方案|策划.*项目|制定.*策略)', message_lower):
            score += 0.3
        
        # 检查多步骤复杂任务
        if len(message) > 100 and re.search(r'(先.*再|然后.*最后|第一步.*第二步.*第三步)', message_lower):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_decomposability(self, message: str) -> float:
        """计算任务可拆解性分数 (0-1)"""
        score = 0.0
        
        message_lower = message.lower()
        
        # 检查执行层任务类型
        for task_type in self.execution_task_types:
            if task_type.lower() in message_lower:
                score += 0.1
        
        # 检查多步骤指示
        if re.search(r'(首先|然后|接着|最后|第一步|第二步|第三步)', message_lower):
            score += 0.2
        
        # 检查批量/多个任务
        if re.search(r'(批量|多个|所有|全部|各|每)', message_lower):
            score += 0.2
        
        # 检查数据源多样性
        if re.search(r'(多个文件|多个来源|多处|不同地方)', message_lower):
            score += 0.2
        
        # 检查处理步骤
        if re.search(r'(先.*再|先.*后|处理.*然后|清洗.*汇总)', message_lower):
            score += 0.2
        
        return min(score, 1.0)
    
    def _requires_direct_delivery(self, message: str) -> bool:
        """判断任务是否需要直接交付给用户"""
        message_lower = message.lower()
        
        # 如果是简单问答或信息请求，直接交付
        if re.search(r'(是什么|为什么|怎么样|如何|怎么|哪里|谁)', message_lower):
            if len(message_lower) < 100:  # 简单问题
                return True
        
        # 如果是操作确认
        if re.search(r'(对吗|是吗|可以吗|行不行|好不好)', message_lower):
            return True
        
        # 如果是简单指令
        if re.search(r'(打开|关闭|启动|停止|创建|删除)', message_lower) and len(message_lower) < 80:
            return True
        
        return False
    
    def _make_routing_decision(self, char_count, word_count, clarity, risk, decomposability, requires_direct_delivery) -> str:
        """根据分析结果做出路由决策"""
        
        # Route D: 信息不足
        if clarity < 0.4:
            return "D: 信息不足 - 请求澄清"
        
        # Route C: 强模型主导
        if risk > 0.3:  # 降低风险阈值
            return "C: 强模型主导 - 高风险/判断类任务"
        
        # Route B: 先拆解再执行
        if decomposability > 0.4:  # 降低拆解阈值
            return "B: 先拆解再执行 - 复合任务/多步骤"
        
        # Route A: 直接执行
        if char_count < self.simple_char_threshold and word_count < self.simple_word_threshold:
            return "A: 直接执行 - 简单清晰任务"
        
        # 默认情况下，如果任务清晰但不可拆解，由强模型处理
        if clarity > 0.6:
            return "C: 强模型主导 - 清晰但不可拆解任务"
        
        # 其他情况由强模型处理
        return "C: 强模型主导 - 默认路由"
    
    def get_execution_prompt(self, task_description: str, route: str) -> Optional[str]:
        """根据路由获取对应的执行层prompt"""
        
        if route.startswith("A:") or route.startswith("B:"):
            # Route A 或 B 需要执行层处理
            return self._get_cheap_model_prompt(task_description)
        else:
            # Route C 或 D 直接由强模型处理
            return None
    
    def _get_cheap_model_prompt(self, task_description: str) -> str:
        """获取低成本执行层prompt模板"""
        
        prompt = """你是一个受限执行器。严格按照指令完成信息处理工作。

## 你的身份
- 你不是最终决策者
- 你只产出中间件，不产出最终结论
- 你的输出会被强模型审核

## 硬性规则
1. 只基于给定材料工作，不引入外部知识
2. 不做价值判断、不给建议、不下结论
3. 找不到就说"Not Found"，不确定就说"Uncertain"
4. 不把推测写成事实
5. 不在信息不足时硬凑完整答案
6. 置信度只填 Low 或 Medium，不允许 High

## 当前任务
""" + task_description + """

## 输出格式（必须严格遵守）

### Task Type
[检索 / 提取 / 清洗 / 摘要 / 分类 / 对比 / 归纳]

### Source Scope
[本次基于哪些材料]

### Evidence Found
[实际找到的证据、片段、关键词、来源位置]

### Extracted Facts
[从证据中明确提取的事实，不写推测]

### Uncertain Points
[证据不足、无法确认、可能冲突的点]

### Missing Information
[还缺什么才能进入下一步]

### Suggested Next Step
[补检索 / 补提取 / 升级强模型 / 可以进入最终汇总]

### Confidence
[Low / Medium]"""
        
        return prompt
    
    def get_reviewer_prompt(self, original_task: str, execution_output: str) -> str:
        """获取强模型Reviewer prompt模板"""
        
        prompt = """你现在需要对以下执行层中间件进行验收。

## 用户原始任务
""" + original_task + """

## 执行层输出
""" + execution_output + """

## 验收维度

1. 事实一致性：中间输出是否真的来自输入证据？有没有编造、扩写、误引？
2. 任务完成度：用户真正的问题是否被回答？是否遗漏关键要求？
3. 逻辑与冲突：多个子结果之间是否矛盾？结论是否跳步？
4. 风险与边界：有没有超出证据边界的说法？语气是否过度自信？
5. 表达与可交付性：结果是否清楚、可用？是否区分了事实/推断/建议？

## 你的判定（三选一）

- **Pass**：证据足够、结论边界清晰、可以直接交付 → 生成最终答复
- **Revise**：有缺口但可补 → 明确指出缺什么，打回执行层补充
- **Take Over**：中间件质量太差或任务超出执行层能力 → 强模型直接接管"""
        
        return prompt
    
    def get_final_checklist(self) -> List[str]:
        """获取最终校验Checklist"""
        return [
            "1. 用户原问题是否被完整回答？",
            "2. 所有重要结论是否能回指到证据？",
            "3. 是否有任何一句话超出证据边界？",
            "4. 是否有遗漏的限制条件？",
            "5. 是否有未处理的冲突？",
            "6. 是否明确区分了事实、推断、建议？",
            "7. 是否标出了不确定性？",
            "8. 当前输出是否达到'可以直接交付'的标准？"
        ]


# 使用示例
if __name__ == "__main__":
    workflow = HybridModelWorkflow()
    
    # 测试不同任务
    test_tasks = [
        "帮我整理一下桌面上的英语学习文件",
        "根据我的英语学习历史，推荐下一步应该学习什么内容？",
        "什么是AI agent？",
        "分析一下这个代码的性能问题",
        "帮我找到昨天讨论的那个Python脚本"
    ]
    
    for task in test_tasks:
        print(f"\n任务: {task}")
        analysis = workflow.analyze_task(task)
        print(f"路由决策: {analysis['routing_decision']}")
        print(f"分析详情: {json.dumps(analysis['task_analysis'], indent=2, ensure_ascii=False)}")