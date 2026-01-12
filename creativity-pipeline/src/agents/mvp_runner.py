"""MVPRunner agent for creating experiments from ideas.

Designs quick MVP experiments for validating ideas.
"""
import re
import json
from typing import Optional, List, Dict, Any

from .base_agent import BaseAgent


class MVPRunnerAgent(BaseAgent):
    """Agent that designs MVP experiments for validated ideas.

    This agent:
    1. Reads confirmed ideas
    2. Designs actionable experiments with tasks
    3. Applies the "three person rule" for validation
    """

    def get_system_prompt(self) -> str:
        return """你是创意流水线的MVP执行代理。你的任务是为确认的创意设计快速验证实验。

实验设计原则：
1. 总时长控制在45分钟内
2. 任务拆分为10分钟左右的小步骤
3. 每个任务有明确的交付物和成功标准
4. 遵循"三人法则"获取反馈

任务设计要求（每个任务）：
- id: 任务ID (如 task-01, task-02)
- description: 具体的任务描述
- time_estimate: 预计时长（分钟，建议10-15分钟）
- deliverable: 明确的交付物
- success_criteria: 可验证的成功标准
- tools: 推荐使用的工具列表
- status: pending

三人法则设计：
- target_profiles: 3个目标用户画像（包含 type 和 where_to_find）
- recruit_script: 招募话术模板
- feedback_template: 反馈收集问卷

任务类型建议：
1. 着陆页/原型制作 (15分钟)
2. 内容准备 (10分钟)
3. 用户招募 (10分钟)
4. 演示/测试 (10分钟)

使用 create_experiment 工具创建实验，确保：
- idea_id: 关联的创意ID
- idea_title: 创意标题
- estimated_time: 总预计时间（不超过45分钟）
- tasks: 任务列表（4-5个任务）
- three_person_rule: 三人法则配置

创建实验后，返回实验ID。
"""

    async def design_experiment(self, idea_id: str) -> Optional[str]:
        """Design experiment for an idea.

        Args:
            idea_id: The idea ID to create experiment for.

        Returns:
            Created experiment ID or None if failed.
        """
        prompt = f"""为创意 {idea_id} 设计一个MVP验证实验。

步骤：
1. 使用 read_ideas 读取创意详情
2. 分析创意的核心假设和验证目标
3. 设计4-5个具体任务
4. 配置三人法则
5. 使用 create_experiment 创建实验

实验设计要点：
- 总时长不超过45分钟
- 每个任务约10分钟
- 有明确的交付物和成功标准
- 三人法则要具体可执行

请开始处理。
"""
        result = await self.run(prompt)
        ids = self._parse_experiment_id(result)
        return ids[0] if ids else None

    def _parse_experiment_id(self, response: str) -> List[str]:
        """Extract experiment ID from agent response.

        Args:
            response: Agent response text containing experiment ID.

        Returns:
            List of experiment IDs found in the response.
        """
        # Match patterns like exp-abc12345 or exp-2026-01-12-001
        pattern = r'exp-[a-f0-9]{8}|exp-\d{4}-\d{2}-\d{2}-\d{3}'
        return re.findall(pattern, response)

    async def generate_tasks(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Generate experiment tasks for an idea (compatibility method for pipeline_handler).

        This method is called by PipelineCallbackHandler to create experiment tasks
        from a confirmed idea dictionary.

        Args:
            idea: Idea dictionary containing id, title, one_liner, problem, etc.

        Returns:
            Dictionary containing experiment data with tasks list and metadata.
        """
        idea_id = idea.get("id", "")
        idea_title = idea.get("title", "未命名创意")
        one_liner = idea.get("one_liner", "")
        problem = idea.get("problem", "")
        mvp_time = idea.get("mvp_time", 45)

        prompt = f"""为以下创意设计一个MVP验证实验：

创意ID: {idea_id}
标题: {idea_title}
一句话描述: {one_liner}
解决问题: {problem}
预计时间: {mvp_time}分钟

请设计实验任务并返回以下JSON格式（不要使用markdown代码块，直接返回JSON）:
{{
    "idea_id": "{idea_id}",
    "idea_title": "{idea_title}",
    "estimated_time": {mvp_time},
    "tasks": [
        {{
            "id": "task-01",
            "description": "任务描述",
            "time_estimate": 10,
            "deliverable": "交付物",
            "success_criteria": "成功标准",
            "tools": ["工具1"],
            "status": "pending"
        }}
    ],
    "three_person_rule": {{
        "target_profiles": [
            {{"type": "用户类型", "where_to_find": "哪里找"}}
        ],
        "recruit_script": "招募话术",
        "feedback_template": "反馈模板"
    }}
}}

请直接返回JSON，不要其他说明。
"""
        result = await self.run(prompt)
        return self._parse_experiment_data(result, idea)

    def _parse_experiment_data(self, response: str, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Parse experiment data from agent response.

        Args:
            response: Agent response text containing JSON experiment data.
            idea: Original idea dictionary for fallback values.

        Returns:
            Experiment dictionary with tasks and metadata.
        """
        # Try to find JSON in response
        try:
            # Look for JSON object pattern
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                data = json.loads(match.group())
                # Validate required fields exist
                if "tasks" in data:
                    return data
        except json.JSONDecodeError:
            pass

        # Fallback: return basic experiment structure
        return {
            "idea_id": idea.get("id", ""),
            "idea_title": idea.get("title", "未命名创意"),
            "estimated_time": idea.get("mvp_time", 45),
            "tasks": [
                {
                    "id": "task-01",
                    "description": "创建项目基础结构",
                    "time_estimate": 10,
                    "deliverable": "项目目录和基础文件",
                    "success_criteria": "项目可运行",
                    "tools": ["IDE"],
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "description": "实现核心功能",
                    "time_estimate": 20,
                    "deliverable": "可演示的原型",
                    "success_criteria": "主功能可用",
                    "tools": ["IDE", "AI辅助"],
                    "status": "pending"
                },
                {
                    "id": "task-03",
                    "description": "部署并分享给3人测试",
                    "time_estimate": 15,
                    "deliverable": "部署链接和用户反馈",
                    "success_criteria": "至少收到1条反馈",
                    "tools": ["部署平台"],
                    "status": "pending"
                }
            ],
            "three_person_rule": {
                "target_profiles": [
                    {"type": "目标用户", "where_to_find": "社交媒体"}
                ],
                "recruit_script": "嗨，我在做一个小实验，想邀请你花5分钟试用一下",
                "feedback_template": "用户:\n第一反应:\n是否愿意继续使用:\n改进建议:"
            }
        }
