"""
提示词管理工具
支持系统提示词的外置配置和管理
"""

from typing import Optional, List, Dict, Any, cast
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client
import json
import os


# 默认系统提示词模板
DEFAULT_SYSTEM_PROMPT = """你是客户资源和话术管理专家助手，专注于多产品/业务线的客户关系管理、话术库维护、资料库管理和销售支持。

## 核心能力

### 1. 产品/业务管理
- 创建、查询、更新、删除产品/业务线
- 每个产品有独立的客户池、话术库、资料库
- 产品之间数据不共享

### 2. 资料库管理
- 为每个产品添加资料（产品介绍、常见问题、竞品分析、核心优势、使用案例等）
- 资料可用于话术生成和智能推荐
- 支持资料分类和标签管理

### 3. 客户资源管理
- 管理客户信息（添加、查询、更新、删除、分类）
- 支持按产品筛选客户
- 客户分类：潜在客户、意向客户、成交客户、流失客户

### 4. 智能录入
- 文本解析：粘贴微信对话、邮件内容，自动提取客户信息
- 图片识别：上传名片、截图，AI识别客户信息
- 支持自动保存到客户库

### 5. AI话术生成
- 智能生成话术：基于场景和产品资料自动生成销售话术
- 话术优化：对现有话术进行AI优化改进
- 变体生成：生成多个不同风格的话术版本

### 6. 对话收集
- 保存对话记录：记录电话、微信、邮件等沟通内容
- 对话分析：汇总分析客户沟通历史
- 跟进提醒：记录下一步行动计划

### 7. 话术库管理
- 管理话术（添加、查询、更新、删除）
- 智能推荐话术（基于场景、行业、客户类型）
- 话术分类：开场白、产品介绍、异议处理、成交话术、跟进话术

### 8. 文档处理
- 解析文档（Excel/Word/PDF）
- 批量导入客户/话术

## 工作流程

1. 用户发起请求时，首先确认涉及的产品（如果有多个产品）
2. 根据产品ID进行相应的数据操作
3. 生成话术时，充分利用产品资料库中的信息
4. 记录对话时，提取关键要点和下一步行动
5. 使用Markdown格式回复，使用图标增强可读性

## 回复风格

- ✅ 成功操作
- ❌ 失败或错误
- 📋 列表信息
- 💡 建议和推荐
- 📊 统计数据
- 🤖 AI生成
- 👤 人工创建
- 📚 资料库
- 🏷️ 产品标签
- 📷 图片识别
- 📝 文本解析
- 💬 对话记录"""


@tool
def get_system_prompt(
    runtime: ToolRuntime = None
) -> str:
    """
    获取当前系统提示词。
    
    返回当前Agent使用的系统提示词配置。
    
    Returns:
        系统提示词内容
    """
    ctx = runtime.context if runtime else new_context(method="get_system_prompt")
    
    try:
        workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
        config_path = os.path.join(workspace_path, "config/agent_llm_config.json")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        current_sp = cfg.get("sp", DEFAULT_SYSTEM_PROMPT)
        
        return f"""📋 当前系统提示词配置

━━━━━━━━━━━━━━━━━━━━━━━━━━

{current_sp}

━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 提示：如需修改系统提示词，请使用 update_system_prompt 工具"""
            
    except Exception as e:
        return f"❌ 获取系统提示词失败：{str(e)}\n\n使用默认提示词。"


@tool
def update_system_prompt(
    new_prompt: str,
    runtime: ToolRuntime = None
) -> str:
    """
    更新系统提示词。
    
    修改Agent使用的系统提示词配置，立即生效。
    
    Args:
        new_prompt: 新的系统提示词内容
    
    Returns:
        更新结果
    """
    ctx = runtime.context if runtime else new_context(method="update_system_prompt")
    
    try:
        workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
        config_path = os.path.join(workspace_path, "config/agent_llm_config.json")
        
        # 读取当前配置
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        old_prompt = cfg.get("sp", "")
        
        # 更新提示词
        cfg["sp"] = new_prompt
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        
        return f"""✅ 系统提示词已更新

📋 更新摘要：
- 原提示词长度：{len(old_prompt)} 字符
- 新提示词长度：{len(new_prompt)} 字符

💡 提示：新提示词将在下次对话时生效。如需恢复默认，请使用 reset_system_prompt 工具。"""
            
    except Exception as e:
        return f"❌ 更新系统提示词失败：{str(e)}"


@tool
def reset_system_prompt(
    runtime: ToolRuntime = None
) -> str:
    """
    重置系统提示词为默认值。
    
    恢复使用系统默认的提示词配置。
    
    Returns:
        重置结果
    """
    ctx = runtime.context if runtime else new_context(method="reset_system_prompt")
    
    try:
        workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
        config_path = os.path.join(workspace_path, "config/agent_llm_config.json")
        
        # 读取当前配置
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        old_prompt = cfg.get("sp", "")
        
        # 重置为默认提示词
        cfg["sp"] = DEFAULT_SYSTEM_PROMPT
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        
        return f"""✅ 系统提示词已重置为默认值

📋 重置摘要：
- 原提示词长度：{len(old_prompt)} 字符
- 默认提示词长度：{len(DEFAULT_SYSTEM_PROMPT)} 字符

💡 默认提示词包含以下核心能力：
- 产品/业务管理
- 资料库管理
- 客户资源管理
- 智能录入
- AI话术生成
- 对话收集
- 话术库管理
- 文档处理"""
            
    except Exception as e:
        return f"❌ 重置系统提示词失败：{str(e)}"


@tool
def get_prompt_templates(
    runtime: ToolRuntime = None
) -> str:
    """
    获取预设提示词模板列表。
    
    返回可用的提示词模板，用于快速切换不同风格的Agent。
    
    Returns:
        模板列表
    """
    ctx = runtime.context if runtime else new_context(method="get_prompt_templates")
    
    templates = {
        "default": {
            "name": "默认模板",
            "description": "全面的功能支持，适合日常使用",
            "prompt": DEFAULT_SYSTEM_PROMPT
        },
        "sales_focused": {
            "name": "销售导向模板",
            "description": "侧重销售转化和话术生成",
            "prompt": """你是销售精英助手，专注于帮助用户提升销售业绩。

## 核心能力

### 销售话术生成
- 根据场景快速生成高转化率话术
- 针对异议处理提供专业建议
- 生成跟进和成交话术

### 客户关系管理
- 识别客户需求和痛点
- 记录客户互动历史
- 制定个性化跟进策略

### 销售数据分析
- 分析客户转化漏斗
- 识别高价值客户
- 预测销售机会

## 工作风格

- 积极主动，以结果为导向
- 提供可执行的销售建议
- 使用数据和案例支撑观点
- 💡 始终关注如何帮助用户达成交易"""
        },
        "service_focused": {
            "name": "客服导向模板",
            "description": "侧重客户服务和问题解决",
            "prompt": """你是客户服务专家，专注于提供优质的客户体验。

## 核心能力

### 客户问题处理
- 快速理解客户问题
- 提供清晰的解决方案
- 记录常见问题和解决方法

### 客户关系维护
- 记录客户沟通历史
- 识别客户满意度和情绪
- 跟进客户反馈

### 服务知识管理
- 维护常见问题库
- 整理服务话术
- 优化服务流程

## 工作风格

- 耐心细致，以客户满意为目标
- 使用友好的沟通语气
- 及时跟进和反馈
- 💡 始终关注如何提升客户体验"""
        }
    }
    
    result = "📋 可用提示词模板\n\n"
    result += "━" * 50 + "\n\n"
    
    for key, template in templates.items():
        result += f"【{template['name']}】\n"
        result += f"键值：{key}\n"
        result += f"说明：{template['description']}\n"
        result += f"提示词长度：{len(template['prompt'])} 字符\n\n"
    
    result += "━" * 50 + "\n\n"
    result += "💡 使用 apply_prompt_template 工具应用模板"
    
    return result


@tool
def apply_prompt_template(
    template_key: str = "default",
    runtime: ToolRuntime = None
) -> str:
    """
    应用预设提示词模板。
    
    将系统提示词切换为指定的预设模板。
    
    Args:
        template_key: 模板键值（default/sales_focused/service_focused）
    
    Returns:
        应用结果
    """
    ctx = runtime.context if runtime else new_context(method="apply_prompt_template")
    
    templates = {
        "default": {
            "name": "默认模板",
            "prompt": DEFAULT_SYSTEM_PROMPT
        },
        "sales_focused": {
            "name": "销售导向模板",
            "prompt": """你是销售精英助手，专注于帮助用户提升销售业绩。

## 核心能力

### 销售话术生成
- 根据场景快速生成高转化率话术
- 针对异议处理提供专业建议
- 生成跟进和成交话术

### 客户关系管理
- 识别客户需求和痛点
- 记录客户互动历史
- 制定个性化跟进策略

### 销售数据分析
- 分析客户转化漏斗
- 识别高价值客户
- 预测销售机会

## 工作风格

- 积极主动，以结果为导向
- 提供可执行的销售建议
- 使用数据和案例支撑观点
- 💡 始终关注如何帮助用户达成交易"""
        },
        "service_focused": {
            "name": "客服导向模板",
            "prompt": """你是客户服务专家，专注于提供优质的客户体验。

## 核心能力

### 客户问题处理
- 快速理解客户问题
- 提供清晰的解决方案
- 记录常见问题和解决方法

### 客户关系维护
- 记录客户沟通历史
- 识别客户满意度和情绪
- 跟进客户反馈

### 服务知识管理
- 维护常见问题库
- 整理服务话术
- 优化服务流程

## 工作风格

- 耐心细致，以客户满意为目标
- 使用友好的沟通语气
- 及时跟进和反馈
- 💡 始终关注如何提升客户体验"""
        }
    }
    
    if template_key not in templates:
        return f"❌ 未找到模板：{template_key}\n\n可用模板：{', '.join(templates.keys())}"
    
    template = templates[template_key]
    
    try:
        workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
        config_path = os.path.join(workspace_path, "config/agent_llm_config.json")
        
        # 读取当前配置
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        # 应用模板
        cfg["sp"] = template["prompt"]
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        
        return f"""✅ 已应用提示词模板

📋 模板信息：
- 模板名称：{template['name']}
- 提示词长度：{len(template['prompt'])} 字符

💡 新提示词将在下次对话时生效。"""
            
    except Exception as e:
        return f"❌ 应用模板失败：{str(e)}"
