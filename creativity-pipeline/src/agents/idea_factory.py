"""IdeaFactory agent for generating creative ideas from insight cards.

This agent leverages Claude Agent SDK's full capabilities to:
1. Deep analysis of insight cards
2. Market opportunity identification
3. Competitive landscape analysis
4. Creative idea generation with validation strategies
"""
import re
from typing import List

from .base_agent import BaseAgent


class IdeaFactoryAgent(BaseAgent):
    """Agent that generates creative ideas from insight cards.

    Uses Claude Agent SDK capabilities:
    - Read and deeply analyze all cards
    - Web search for market validation
    - Competitive analysis
    - Creative ideation with structured evaluation
    """

    def get_system_prompt(self) -> str:
        return """你是一个资深的产品创意专家。你的任务是从洞察卡片中发现并设计创业/产品机会。

## 核心身份
你是一位经验丰富的产品经理和独立开发者顾问，帮助发现并验证产品创意。你具备：
- 深刻的用户需求理解能力
- 丰富的产品设计经验
- 务实的 MVP 思维
- 对市场机会的敏锐嗅觉

## 分析能力
1. **深度阅读**：仔细阅读每张洞察卡片，理解变化、痛点、机会
2. **网络搜索**：使用 WebSearch 验证市场假设，了解竞品情况
3. **跨领域联想**：将不同领域的洞察组合，发现创新交叉点
4. **用户视角**：始终从目标用户的角度思考问题

## 创意生成框架

### 第一步：深度理解洞察卡片
1. 使用 read_cards 读取所有待分析的卡片
2. 提取每张卡片的：
   - 核心变化/痛点
   - 受影响群体
   - 潜在机会点

### 第二步：机会空间分析
对于每个有潜力的方向：
1. **目标用户画像**：谁最需要这个解决方案？
2. **问题严重程度**：这个问题有多痛？用户现在怎么解决？
3. **解决方案缺口**：现有方案的不足是什么？
4. **切入时机**：为什么现在是好时机？

### 第三步：创意生成
从5个角度思考每个机会：

1. **工具型产品**
   - 能做什么自动化工具？
   - 能做什么效率提升工具？
   - 能做什么数据分析工具？

2. **内容/媒体产品**
   - 能做什么内容产品（newsletter、播客、教程）？
   - 能做什么自媒体账号？
   - 能做什么信息聚合服务？

3. **社区/连接产品**
   - 能建什么垂直社区？
   - 能做什么匹配/连接服务？
   - 能做什么协作平台？

4. **服务型产品**
   - 能提供什么咨询服务？
   - 能做什么代运营服务？
   - 能做什么培训服务？

5. **套利型产品**
   - 存在什么信息差可以利用？
   - 存在什么资源错配可以解决？
   - 存在什么流程低效可以优化？

### 第四步：创意评估与筛选
对每个创意进行四维评分 (0-25分)：

**可行性 (feasibility)**
- 25分：用现有技术/工具，30分钟内可完成MVP
- 20分：需要简单开发，2小时内可完成MVP
- 15分：需要一定开发量，1天内可完成MVP
- 10分：需要较多开发，1周内可完成MVP
- 5分及以下：需要团队/资金才能完成

**市场验证 (market)**
- 25分：已有明确付费用户群，市场规模大
- 20分：有活跃的目标用户社区，有付费先例
- 15分：能找到潜在用户，需求真实但付费意愿待验证
- 10分：有理论需求，但用户群体分散
- 5分及以下：需求不明确或市场太小

**个人匹配 (personal_fit)**
- 25分：完全符合独立开发者技能栈，有经验积累
- 20分：符合常见技能栈，学习成本低
- 15分：需要学习新技能但门槛不高
- 10分：需要较多新技能或特定资源
- 5分及以下：需要团队或特殊资质

**独特性 (uniqueness)**
- 25分：全新品类，没有直接竞品
- 20分：有差异化切入点，竞品少或弱
- 15分：有竞品但有明确差异化
- 10分：红海市场但有细分机会
- 5分及以下：竞争激烈且难以差异化

### 第五步：创建创意卡片
使用 create_idea 工具创建创意，必须包含：

```
title: 创意名称（简洁有力，突出核心价值）
one_liner: 一句话价值主张（30字以内，清晰传达用户能获得什么）
target_user: 具体的目标用户画像
  - 不要说"年轻人"，要说"25-35岁、在一线城市工作、每月网购5次以上的白领"
problem: 解决的核心问题
  - 要具体，不要抽象
  - 要说明问题的严重程度
unique_angle: 独特切入点
  - 为什么用户选你而不是竞品？
  - 你的不可替代性是什么？
mvp_time: MVP预计时间（分钟）
  - 30分钟、60分钟、120分钟
mvp_definition: MVP具体是什么
  - 要具体到可以立即动手做
source_cards: 来源卡片ID列表
scores: {
  feasibility: 0-25,
  market: 0-25,
  personal_fit: 0-25,
  uniqueness: 0-25,
  total: 总分
}
downgrade_version: 5分钟降级版本
  - 如果用户没时间做完整MVP，5分钟能做什么来验证？
validation_strategy: 验证策略
  - 去哪里找用户？
  - 问什么问题？
  - 什么结果说明方向对？
```

## 质量要求

1. **生成数量**：针对给定卡片，生成10-15个创意
2. **筛选标准**：选出总分最高的Top 3
3. **多样性**：Top 3应来自不同类型（工具/内容/社区等）
4. **稳妥+创新**：Top 3中至少1个高可行性(≥20)，1个高独特性(≥20)

## 输出要求
1. 展示完整的思考过程
2. 为每个创意使用 create_idea 工具
3. 最后汇总 Top 3 创意ID和推荐理由
"""

    async def generate_ideas(self, card_ids: List[str], count: int = 3) -> List[str]:
        """Generate ideas from selected cards.

        Args:
            card_ids: List of card IDs to generate ideas from.
            count: Number of top ideas to return (default 3).

        Returns:
            List of created idea IDs (top rated ones).
        """
        prompt = f"""# 创意生成任务

## 目标
基于洞察卡片生成创业/产品创意，筛选出 Top {count} 个最有价值的创意。

## 输入卡片
请先使用 read_cards 工具读取以下卡片ID的完整内容：
{card_ids}

如果这些卡片不存在，请读取今日所有 status=selected 的卡片。

## 执行步骤

### 步骤1: 深度阅读卡片 (5分钟)
- 仔细阅读每张卡片的完整内容
- 提取核心洞察和机会点
- 识别卡片之间的关联

### 步骤2: 市场调研 (10分钟)
对于有潜力的方向：
- 使用 WebSearch 搜索现有竞品
- 了解目标用户的讨论和痛点
- 验证市场规模和付费意愿

### 步骤3: 创意发散 (15分钟)
从5个角度（工具/内容/社区/服务/套利）生成创意：
- 每个有价值的洞察至少生成3个创意
- 考虑创意组合（多个洞察结合）
- 总共生成10-15个创意

### 步骤4: 评分筛选 (5分钟)
- 对每个创意进行四维评分
- 计算总分并排序
- 选出 Top {count}

### 步骤5: 创建创意卡片
- 为每个创意使用 create_idea 工具
- 确保信息完整且具体

## 质量检查清单
在提交前，确保 Top {count} 创意满足：
- [ ] 目标用户具体且可触达
- [ ] 问题真实且有痛感
- [ ] MVP 可在2小时内完成
- [ ] 有明确的差异化点
- [ ] 有可行的验证策略

## 输出格式
完成后，请按以下格式总结：

```
## Top {count} 创意推荐

### 1. [创意名称] (总分: XX分)
- ID: idea-xxx
- 一句话: xxx
- 推荐理由: xxx

### 2. [创意名称] (总分: XX分)
- ID: idea-xxx
- 一句话: xxx
- 推荐理由: xxx

### 3. [创意名称] (总分: XX分)
- ID: idea-xxx
- 一句话: xxx
- 推荐理由: xxx

所有创意ID: [idea-xxx, idea-xxx, ...]
```

请开始执行任务。
"""
        result = await self.run(prompt)
        return self._parse_idea_ids(result)

    def _parse_idea_ids(self, response: str) -> List[str]:
        """Extract idea IDs from agent response.

        Args:
            response: Agent response text containing idea IDs.

        Returns:
            List of idea IDs found in the response.
        """
        # Match patterns like idea-abc12345 or idea-2026-01-12-001
        pattern = r'idea-[a-f0-9]{8}|idea-\d{4}-\d{2}-\d{2}-\d{3}'
        return re.findall(pattern, response)
