"""
LLM摘要模块 - 使用大语言模型对新闻来源进行智能总结
支持多个LLM提供商: OpenAI, Anthropic, Ollama, Qwen, DeepSeek
"""

import json
import requests
from typing import List, Dict, Optional, Tuple


class LLMSummarizer:
    """LLM摘要生成器"""

    def __init__(self, config: Dict):
        """
        初始化LLM摘要生成器

        Args:
            config: LLM配置字典，包含provider, api_key, model等
        """
        self.provider = config.get("LLM_PROVIDER", "openai").lower()
        self.api_key = config.get("LLM_API_KEY", "")
        self.model = config.get("LLM_MODEL", "gpt-4o-mini")
        self.base_url = config.get("LLM_BASE_URL", "")
        self.max_tokens = config.get("LLM_MAX_TOKENS", 150)
        self.temperature = config.get("LLM_TEMPERATURE", 0.3)

        # 设置默认API端点
        if not self.base_url:
            if self.provider == "openai":
                self.base_url = "https://api.openai.com/v1"
            elif self.provider == "anthropic":
                self.base_url = "https://api.anthropic.com/v1"
            elif self.provider == "ollama":
                self.base_url = "http://localhost:11434/v1"
            elif self.provider in ["qwen", "tongyi"]:
                self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            elif self.provider == "deepseek":
                self.base_url = "https://api.deepseek.com/v1"

    def summarize_source(
        self, source_name: str, titles: List[str], count: int = None
    ) -> Tuple[bool, str]:
        """
        对单个来源的标题列表生成摘要

        Args:
            source_name: 来源名称（如"微博热搜"）
            titles: 标题列表
            count: 总条数（可选）

        Returns:
            (success, summary_text): 成功标志和摘要文本
        """
        if not titles:
            return False, "没有标题可以总结"

        if not self.api_key and self.provider != "ollama":
            return False, "未配置API密钥"

        # 构建提示词
        titles_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])
        prompt = f"""你是一个新闻摘要助手。请用1-2句话总结以下{source_name}的主要热点：

{titles_text}

要求：
- 简洁明了，不超过50字
- 提炼核心主题
- 如果有多个不同主题，用顿号分隔
- 不要使用"主要关注"等开头，直接说主题"""

        try:
            # 根据不同提供商调用API
            if self.provider in ["openai", "ollama", "qwen", "deepseek"]:
                return self._call_openai_compatible(prompt)
            elif self.provider == "anthropic":
                return self._call_anthropic(prompt)
            else:
                return False, f"不支持的LLM提供商: {self.provider}"

        except Exception as e:
            return False, f"LLM调用失败: {str(e)}"

    def _call_openai_compatible(self, prompt: str) -> Tuple[bool, str]:
        """调用OpenAI兼容的API"""
        url = f"{self.base_url}/chat/completions"

        headers = {"Content-Type": "application/json"}

        # Ollama本地部署不需要API key
        if self.provider != "ollama":
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            summary = result["choices"][0]["message"]["content"].strip()

            return True, summary

        except requests.exceptions.Timeout:
            return False, "API调用超时"
        except requests.exceptions.RequestException as e:
            return False, f"API调用失败: {str(e)}"
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return False, f"解析响应失败: {str(e)}"

    def _call_anthropic(self, prompt: str) -> Tuple[bool, str]:
        """调用Anthropic Claude API"""
        url = f"{self.base_url}/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            summary = result["content"][0]["text"].strip()

            return True, summary

        except requests.exceptions.Timeout:
            return False, "API调用超时"
        except requests.exceptions.RequestException as e:
            return False, f"API调用失败: {str(e)}"
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return False, f"解析响应失败: {str(e)}"


def generate_source_summaries(
    source_data_list: List[Dict], llm_config: Dict
) -> Dict[str, str]:
    """
    批量生成来源摘要

    Args:
        source_data_list: 来源数据列表，每个包含source_id, source_name, titles
        llm_config: LLM配置

    Returns:
        {source_id: summary_text} 字典
    """
    summarizer = LLMSummarizer(llm_config)
    summaries = {}

    for source_data in source_data_list:
        source_id = source_data.get("source_id", "")
        source_name = source_data.get("source_name", "")
        titles = [t["title"] for t in source_data.get("titles", [])]

        if not titles:
            continue

        success, summary = summarizer.summarize_source(source_name, titles, len(titles))

        if success:
            summaries[source_id] = summary
        else:
            # LLM失败时回退到简单模式
            # 显示前3条标题
            preview_titles = titles[:3]
            if len(titles) > 3:
                summaries[source_id] = (
                    f"{', '.join(preview_titles[:2])}等{len(titles)}个热点"
                )
            else:
                summaries[source_id] = ", ".join(preview_titles)

    return summaries
