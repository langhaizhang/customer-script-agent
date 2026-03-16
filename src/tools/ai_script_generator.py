"""
AI话术生成工具
基于产品资料库智能生成销售话术
"""

from typing import Optional, List, Dict, Any, cast
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage
from storage.database.supabase_client import get_supabase_client
import json
import re


def get_text_content(content) -> str:
    """安全地从 AIMessage content 提取文本"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
    else:
        return str(content)


# 话术分类说明
SCRIPT_CATEGORIES = {
    "opening": "开场白 - 首次联系客户时使用",
    "introduction": "产品介绍 - 介绍产品特点和优势",
    "objection": "异议处理 - 应对客户疑虑和反对意见",
    "closing": "成交话术 - 推动客户做出购买决定",
    "follow_up": "跟进话术 - 维护客户关系和后续联系",
    "general": "通用话术 - 适用于多种场景"
}


@tool
def generate_script(
    product_id: int,
    category: str,
    scenario: str,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    auto_save: bool = True,
    runtime: ToolRuntime = None
) -> str:
    """
    AI智能生成销售话术。
    
    基于产品资料库内容，智能生成适合特定场景的销售话术。
    生成的話术会自动标记为AI生成，便于后续管理。
    
    Args:
        product_id: 产品ID（必填），用于获取产品资料
        category: 话术分类（opening/introduction/objection/closing/follow_up/general）
        scenario: 使用场景描述，如"首次联系互联网行业潜在客户"
        industry: 目标行业，可选
        customer_type: 目标客户类型，可选
        keywords: 关键词标签，可选
        auto_save: 是否自动保存到话术库，默认True
    
    Returns:
        生成的话术内容
    """
    ctx = runtime.context if runtime else new_context(method="generate_script")
    
    try:
        db_client = get_supabase_client(ctx)
        
        # 1. 获取产品信息
        product_response = db_client.table('products').select('*').eq('id', product_id).execute()
        if not product_response.data or len(product_response.data) == 0:
            return f"❌ 未找到产品ID {product_id}，请确认产品是否存在"
        
        product = cast(Dict[str, Any], product_response.data[0])
        product_name = product.get('name', '未知产品')
        product_description = product.get('description', '')
        
        # 2. 获取产品相关资料
        knowledge_response = db_client.table('knowledge_base').select('*').eq('product_id', product_id).execute()
        knowledge_list = knowledge_response.data or []
        
        # 构建资料上下文
        knowledge_context = ""
        if knowledge_list:
            knowledge_context = "\n\n📚 产品资料库：\n"
            for k_item in knowledge_list[:10]:  # 最多取10条
                k_dict = cast(Dict[str, Any], k_item)
                knowledge_context += f"\n【{k_dict.get('title', '未命名')}】\n{k_dict.get('content', '')}\n"
        else:
            knowledge_context = "\n\n⚠️ 该产品暂无资料库内容，建议先添加产品资料以获得更好的话术效果。"
        
        # 3. 获取该产品已有话术作为参考
        scripts_response = db_client.table('scripts').select('*').eq('product_id', product_id).eq('category', category).execute()
        existing_scripts = scripts_response.data or []
        
        reference_scripts = ""
        if existing_scripts:
            reference_scripts = "\n\n📝 参考话术（同类优秀话术）：\n"
            # 取评分最高的3条
            def get_score(x):
                x_dict = cast(Dict[str, Any], x)
                return x_dict.get('effectiveness_score', 0) or 0
            sorted_scripts = sorted(existing_scripts, key=get_score, reverse=True)[:3]
            for s_item in sorted_scripts:
                s_dict = cast(Dict[str, Any], s_item)
                reference_scripts += f"\n「{s_dict.get('title', '')}」\n{s_dict.get('content', '')}\n"
        
        # 4. 调用LLM生成话术
        client = LLMClient(ctx=ctx)
        
        category_desc = SCRIPT_CATEGORIES.get(category, "通用话术")
        
        system_prompt = f"""你是一位资深的销售话术专家，擅长撰写高质量的销售话术。

你的任务是根据产品信息和场景需求，生成专业、有效的销售话术。

## 话术要求

1. **针对性**：紧扣场景需求，语言自然流畅
2. **专业性**：体现产品优势，解决客户痛点
3. **说服力**：运用销售技巧，引导客户行动
4. **实用性**：简洁有力，便于记忆和使用

## 话术分类说明
{category_desc}

## 输出格式

请严格按以下JSON格式输出：
{{
    "title": "话术标题",
    "content": "话术正文内容",
    "tips": ["使用技巧1", "使用技巧2"],
    "expected_response": "预期的客户反应"
}}

注意：
- content字段应该是完整的话术内容，可以分段但不要过于冗长
- tips字段提供2-3条使用建议
- 不要输出任何JSON之外的内容"""

        user_prompt = f"""请为以下场景生成销售话术：

## 产品信息
- 产品名称：{product_name}
- 产品描述：{product_description or '暂无'}
{knowledge_context}
{reference_scripts}

## 生成需求
- 话术分类：{category_desc}
- 使用场景：{scenario}
- 目标行业：{industry or '不限'}
- 客户类型：{customer_type or '不限'}
- 关键词：{', '.join(keywords) if keywords else '无特定要求'}

请生成专业、有效的销售话术。"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = client.invoke(
            messages=messages,
            model="doubao-seed-1-8-251228",
            temperature=0.8  # 稍高温度增加创意
        )
        
        response_text = get_text_content(response.content).strip()
        
        # 解析JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            script_data = json.loads(json_match.group())
        else:
            # 如果解析失败，使用原始文本
            script_data = {
                "title": f"{scenario}话术",
                "content": response_text,
                "tips": [],
                "expected_response": ""
            }
        
        # 5. 保存到数据库
        if auto_save:
            save_data: Dict[str, Any] = {
                "title": script_data.get("title", f"{scenario}话术"),
                "content": script_data.get("content", ""),
                "product_id": product_id,
                "category": category,
                "scenario": scenario,
                "is_ai_generated": True
            }
            
            if industry:
                save_data["industry"] = industry
            if customer_type:
                save_data["customer_type"] = customer_type
            if keywords:
                save_data["keywords"] = keywords
            
            save_response = db_client.table('scripts').insert(save_data).execute()
            
            if save_response.data and len(save_response.data) > 0:
                saved = cast(Dict[str, Any], save_response.data[0])
                script_data['id'] = saved.get('id')
                script_data['saved'] = True
        
        # 6. 格式化输出
        result = f"""🤖 AI话术生成成功

📦 产品：{product_name}
📂 分类：{category_desc}
🎯 场景：{scenario}

━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 「{script_data.get('title', '未命名')}」

{script_data.get('content', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        if script_data.get('tips'):
            result += "\n\n💡 使用技巧："
            for tip in script_data.get('tips', []):
                result += f"\n  • {tip}"
        
        if script_data.get('expected_response'):
            result += f"\n\n🔮 预期客户反应：{script_data.get('expected_response')}"
        
        if script_data.get('saved'):
            result += f"\n\n✅ 已自动保存到话术库，话术ID: {script_data.get('id')}"
        
        return result
            
    except json.JSONDecodeError as e:
        return f"❌ 解析AI响应失败：{str(e)}"
    except Exception as e:
        return f"❌ 生成话术失败：{str(e)}"


@tool
def improve_script(
    script_id: int,
    improvement_focus: str = "effectiveness",
    runtime: ToolRuntime = None
) -> str:
    """
    AI优化已有话术。
    
    基于销售最佳实践，对现有话术进行优化改进。
    
    Args:
        script_id: 要优化的话术ID
        improvement_focus: 优化重点（effectiveness/professional/persuasive/concise）
            - effectiveness: 提升有效性
            - professional: 提升专业性
            - persuasive: 增强说服力
            - concise: 精简内容
    
    Returns:
        优化后的话术
    """
    ctx = runtime.context if runtime else new_context(method="improve_script")
    
    try:
        db_client = get_supabase_client(ctx)
        
        # 获取原话术
        script_response = db_client.table('scripts').select('*').eq('id', script_id).execute()
        if not script_response.data or len(script_response.data) == 0:
            return f"❌ 未找到话术ID {script_id}"
        
        original_script = cast(Dict[str, Any], script_response.data[0])
        
        # 获取产品资料
        product_id = original_script.get('product_id')
        knowledge_context = ""
        
        if product_id:
            knowledge_response = db_client.table('knowledge_base').select('*').eq('product_id', product_id).execute()
            knowledge_list = knowledge_response.data or []
            if knowledge_list:
                knowledge_context = "\n\n📚 产品资料：\n"
                for k_item in knowledge_list[:5]:
                    k_dict = cast(Dict[str, Any], k_item)
                    content = k_dict.get('content', '') or ''
                    knowledge_context += f"- {k_dict.get('title')}: {content[:200]}...\n"
        
        # 优化方向说明
        focus_map = {
            "effectiveness": "提升话术的有效性，使其更容易达成销售目标",
            "professional": "提升专业度，使用更专业的表达和术语",
            "persuasive": "增强说服力，加入更强的引导和促单元素",
            "concise": "精简内容，去除冗余，使话术更加简洁有力"
        }
        
        client = LLMClient(ctx=ctx)
        
        system_prompt = """你是一位资深的销售话术优化专家。
你的任务是根据优化方向，对现有话术进行改进。

优化原则：
1. 保持原话术的核心意图和场景
2. 针对优化方向进行针对性改进
3. 提供具体的优化说明

请按以下JSON格式输出：
{
    "improved_title": "优化后的标题",
    "improved_content": "优化后的内容",
    "changes": ["修改点1", "修改点2"],
    "why_better": "优化说明"
}"""

        user_prompt = f"""请优化以下销售话术：

## 原话术
标题：{original_script.get('title', '')}
内容：{original_script.get('content', '')}
场景：{original_script.get('scenario', '未指定')}
分类：{original_script.get('category', 'general')}
{knowledge_context}

## 优化方向
{focus_map.get(improvement_focus, '综合优化')}

请提供优化后的话术。"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = client.invoke(
            messages=messages,
            model="doubao-seed-1-8-251228",
            temperature=0.7
        )
        
        response_text = get_text_content(response.content).strip()
        
        # 解析结果
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            improved_data = json.loads(json_match.group())
        else:
            return "❌ AI优化结果解析失败，请重试"
        
        # 更新数据库
        update_data = {
            "title": improved_data.get("improved_title", original_script.get("title")),
            "content": improved_data.get("improved_content", original_script.get("content")),
            "is_ai_generated": True
        }
        
        db_client.table('scripts').update(update_data).eq('id', script_id).execute()
        
        result = f"""🤖 话术优化完成

## 优化后的話术

📝 「{improved_data.get('improved_title', '')}」

{improved_data.get('improved_content', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 主要修改：
"""
        for change in improved_data.get('changes', []):
            result += f"  • {change}\n"
        
        result += f"\n💡 优化说明：{improved_data.get('why_better', '')}"
        result += f"\n\n✅ 已更新话术库"
        
        return result
            
    except Exception as e:
        return f"❌ 优化话术失败：{str(e)}"


@tool
def generate_script_variants(
    script_id: int,
    count: int = 3,
    runtime: ToolRuntime = None
) -> str:
    """
    生成话术变体版本。
    
    基于已有话术生成多个不同风格的变体版本，供选择使用。
    
    Args:
        script_id: 原话术ID
        count: 生成变体数量，默认3个，最多5个
    
    Returns:
        多个话术变体
    """
    ctx = runtime.context if runtime else new_context(method="generate_script_variants")
    
    try:
        db_client = get_supabase_client(ctx)
        
        # 获取原话术
        script_response = db_client.table('scripts').select('*').eq('id', script_id).execute()
        if not script_response.data or len(script_response.data) == 0:
            return f"❌ 未找到话术ID {script_id}"
        
        original = cast(Dict[str, Any], script_response.data[0])
        
        # 限制数量
        count = min(count, 5)
        
        client = LLMClient(ctx=ctx)
        
        system_prompt = """你是一位销售话术创意专家。
你的任务是基于原话术生成多个不同风格的变体版本。

变体风格包括：
1. 亲和型：更加亲切友好，拉近距离
2. 专业型：更加正式专业，展示实力
3. 问题型：以提问引导，激发需求
4. 故事型：通过案例故事打动客户
5. 数据型：用数据和事实说话

请按JSON数组格式输出变体：
[
    {
        "style": "风格名称",
        "title": "话术标题",
        "content": "话术内容",
        "best_for": "最适合的场景"
    }
]"""

        user_prompt = f"""请基于以下话术生成{count}个不同风格的变体：

## 原话术
标题：{original.get('title', '')}
内容：{original.get('content', '')}
场景：{original.get('scenario', '未指定')}

请生成{count}个风格各异的变体版本。"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = client.invoke(
            messages=messages,
            model="doubao-seed-1-8-251228",
            temperature=0.9
        )
        
        response_text = get_text_content(response.content).strip()
        
        # 解析结果
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            variants = json.loads(json_match.group())
        else:
            return "❌ 变体生成失败，请重试"
        
        # 保存变体到数据库
        saved_ids = []
        for variant in variants[:count]:
            save_data = {
                "title": variant.get("title", original.get("title")),
                "content": variant.get("content", ""),
                "product_id": original.get("product_id"),
                "category": original.get("category", "general"),
                "scenario": original.get("scenario"),
                "is_ai_generated": True
            }
            
            save_response = db_client.table('scripts').insert(save_data).execute()
            if save_response.data and len(save_response.data) > 0:
                saved = cast(Dict[str, Any], save_response.data[0])
                saved_ids.append(saved.get('id'))
        
        # 格式化输出
        result = f"🤖 已生成 {len(variants[:count])} 个话术变体\n\n"
        result += f"📌 原话术：{original.get('title', '')}\n"
        result += "━" * 40 + "\n\n"
        
        for i, v in enumerate(variants[:count], 1):
            result += f"【变体{i}】{v.get('style', '通用')}风格\n"
            result += f"📝 「{v.get('title', '')}」\n"
            result += f"{v.get('content', '')}\n"
            result += f"🎯 最适合：{v.get('best_for', '通用场景')}\n"
            if i <= len(saved_ids):
                result += f"✅ 已保存，ID: {saved_ids[i-1]}\n"
            result += "\n" + "━" * 40 + "\n\n"
        
        return result
            
    except Exception as e:
        return f"❌ 生成变体失败：{str(e)}"
