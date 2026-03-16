"""
智能录入工具模块

提供文本解析和图片识别功能，自动提取客户信息。
支持：
1. 文本解析：粘贴文字自动提取客户信息
2. 图片识别：上传名片/截图自动识别（多模态）
"""

from typing import Optional, Dict, Any, cast
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


@tool
def parse_text_to_customer(
    text: str,
    product_id: int = 0,
    auto_save: bool = False,
    runtime: ToolRuntime = None
) -> str:
    """
    从文本中智能解析客户信息。
    
    支持解析微信对话、邮件内容、会议记录等非结构化文本，
    自动提取客户姓名、公司、电话、邮箱等信息。
    
    Args:
        text: 要解析的文本内容，如微信聊天记录、邮件内容等
        product_id: 关联的产品ID，可选。如果提供并设置auto_save=True，会自动保存
        auto_save: 是否自动保存到数据库，默认False只返回解析结果
    
    Returns:
        解析出的客户信息，JSON格式
    """
    ctx = runtime.context if runtime else new_context(method="parse_text_to_customer")
    
    try:
        client = LLMClient(ctx=ctx)
        
        system_prompt = """你是一个客户信息提取专家。请从用户提供的文本中提取客户信息。

需要提取的字段：
- name: 客户姓名
- company: 公司名称
- phone: 联系电话
- email: 邮箱地址
- industry: 所属行业
- notes: 其他备注信息

输出要求：
1. 必须输出JSON格式，不要有其他内容
2. 如果某个字段无法提取，设为null
3. 如果文本中没有客户信息，返回空对象 {}

输出格式示例：
{
    "name": "张三",
    "company": "科技有限公司",
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "industry": "互联网",
    "notes": "对产品A感兴趣，预算约50万"
}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请从以下文本中提取客户信息：\n\n{text}")
        ]
        
        response = client.invoke(
            messages=messages,
            model="doubao-seed-1-8-251228",
            temperature=0.1
        )
        
        response_text = get_text_content(response.content).strip()
        
        # 提取JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            customer_info = json.loads(json_match.group())
        else:
            customer_info = {}
        
        # 验证是否提取到有效信息
        if not customer_info.get('name'):
            return """❌ 未能从文本中识别出客户信息

💡 提示：
- 请确保文本中包含客户姓名
- 文本可以是微信对话、邮件内容、会议记录等
- 示例："王经理，13800138000，阿里巴巴，想了解我们的产品"

📋 您提供的文本：
""" + text[:200] + ("..." if len(text) > 200 else "")
        
        # 如果需要自动保存
        if auto_save and product_id > 0:
            db_client = get_supabase_client(ctx)
            
            save_data: Dict[str, Any] = {
                "name": customer_info.get("name"),
                "customer_type": "potential",
                "status": "active",
                "source": "智能录入-文本"
            }
            
            if product_id:
                save_data["product_id"] = product_id
            if customer_info.get("company"):
                save_data["company"] = customer_info.get("company")
            if customer_info.get("phone"):
                save_data["phone"] = customer_info.get("phone")
            if customer_info.get("email"):
                save_data["email"] = customer_info.get("email")
            if customer_info.get("industry"):
                save_data["industry"] = customer_info.get("industry")
            if customer_info.get("notes"):
                save_data["notes"] = customer_info.get("notes")
            
            save_response = db_client.table('customers').insert(save_data).execute()
            
            if save_response.data and len(save_response.data) > 0:
                saved = cast(Dict[str, Any], save_response.data[0])
                customer_info['id'] = saved.get('id')
                customer_info['saved'] = True
        
        result = f"""✅ 成功从文本中识别客户信息

📋 识别结果：
- 姓名: {customer_info.get('name', '未识别')}
- 公司: {customer_info.get('company', '未识别')}
- 电话: {customer_info.get('phone', '未识别')}
- 邮箱: {customer_info.get('email', '未识别')}
- 行业: {customer_info.get('industry', '未识别')}
- 备注: {customer_info.get('notes', '无')}"""

        if customer_info.get('saved'):
            result += f"\n\n✅ 已自动保存到数据库，客户ID: {customer_info.get('id')}"
        else:
            result += "\n\n💡 如需保存，请告诉我" + (f"并关联到产品ID {product_id}" if product_id else "")
        
        return result
            
    except Exception as e:
        return f"❌ 解析文本失败: {str(e)}"


@tool
def parse_image_to_customer(
    image_url: str,
    product_id: int = 0,
    auto_save: bool = False,
    runtime: ToolRuntime = None
) -> str:
    """
    从图片中智能识别客户信息。
    
    支持识别名片、截图、文档图片等，自动提取客户姓名、公司、电话、邮箱等信息。
    需要提供图片的公开访问URL。
    
    Args:
        image_url: 图片的URL地址，必须是公开可访问的
        product_id: 关联的产品ID，可选
        auto_save: 是否自动保存到数据库，默认False只返回识别结果
    
    Returns:
        识别出的客户信息，JSON格式
    """
    ctx = runtime.context if runtime else new_context(method="parse_image_to_customer")
    
    try:
        client = LLMClient(ctx=ctx)
        
        system_prompt = """你是一个名片和文档识别专家。请从图片中提取客户信息。

需要提取的字段：
- name: 客户姓名
- company: 公司名称
- phone: 联系电话
- email: 邮箱地址
- industry: 所属行业
- title: 职位
- address: 地址
- notes: 其他备注信息

输出要求：
1. 必须输出JSON格式，不要有其他内容
2. 如果某个字段无法识别，设为null
3. 如果图片中没有客户信息，返回空对象 {}

输出格式示例：
{
    "name": "张三",
    "company": "科技有限公司",
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "industry": "互联网",
    "title": "产品经理",
    "address": "北京市朝阳区xxx",
    "notes": ""
}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": "请识别这张图片中的客户信息，提取姓名、公司、电话、邮箱等字段。"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }
            ])
        ]
        
        response = client.invoke(
            messages=messages,
            model="doubao-seed-1-6-vision-250815",  # 使用视觉模型
            temperature=0.1
        )
        
        response_text = get_text_content(response.content).strip()
        
        # 提取JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            customer_info = json.loads(json_match.group())
        else:
            customer_info = {}
        
        # 验证是否识别到有效信息
        if not customer_info.get('name'):
            return """❌ 未能从图片中识别出客户信息

💡 提示：
- 请确保图片清晰可读
- 支持识别名片、截图、文档图片等
- 图片必须是公开可访问的URL地址

📷 您提供的图片URL：
""" + image_url
        
        # 如果需要自动保存
        if auto_save and product_id > 0:
            db_client = get_supabase_client(ctx)
            
            save_data: Dict[str, Any] = {
                "name": customer_info.get("name"),
                "customer_type": "potential",
                "status": "active",
                "source": "智能录入-图片"
            }
            
            if product_id:
                save_data["product_id"] = product_id
            if customer_info.get("company"):
                save_data["company"] = customer_info.get("company")
            if customer_info.get("phone"):
                save_data["phone"] = customer_info.get("phone")
            if customer_info.get("email"):
                save_data["email"] = customer_info.get("email")
            if customer_info.get("industry"):
                save_data["industry"] = customer_info.get("industry")
            if customer_info.get("title"):
                notes = f"职位: {customer_info.get('title')}"
                if customer_info.get("address"):
                    notes += f"\n地址: {customer_info.get('address')}"
                save_data["notes"] = notes
            elif customer_info.get("notes"):
                save_data["notes"] = customer_info.get("notes")
            
            save_response = db_client.table('customers').insert(save_data).execute()
            
            if save_response.data and len(save_response.data) > 0:
                saved = cast(Dict[str, Any], save_response.data[0])
                customer_info['id'] = saved.get('id')
                customer_info['saved'] = True
        
        result = f"""✅ 成功从图片中识别客户信息

📋 识别结果：
- 姓名: {customer_info.get('name', '未识别')}
- 公司: {customer_info.get('company', '未识别')}
- 职位: {customer_info.get('title', '未识别')}
- 电话: {customer_info.get('phone', '未识别')}
- 邮箱: {customer_info.get('email', '未识别')}
- 行业: {customer_info.get('industry', '未识别')}
- 地址: {customer_info.get('address', '未识别')}"""

        if customer_info.get('saved'):
            result += f"\n\n✅ 已自动保存到数据库，客户ID: {customer_info.get('id')}"
        else:
            result += "\n\n💡 如需保存，请告诉我" + (f"并关联到产品ID {product_id}" if product_id else "")
        
        return result
            
    except Exception as e:
        return f"❌ 识别图片失败: {str(e)}"


@tool
def smart_add_customer(
    content: str,
    content_type: str = "text",
    product_id: int = 0,
    runtime: ToolRuntime = None
) -> str:
    """
    智能添加客户（统一入口）。
    
    根据内容类型自动选择文本解析或图片识别，提取客户信息并保存。
    
    Args:
        content: 内容。如果是text类型，传入文字内容；如果是image类型，传入图片URL
        content_type: 内容类型，"text" 或 "image"
        product_id: 关联的产品ID
    
    Returns:
        识别结果和保存状态
    """
    ctx = runtime.context if runtime else new_context(method="smart_add_customer")
    
    if content_type == "image":
        return parse_image_to_customer(
            image_url=content,
            product_id=product_id,
            auto_save=True,
            runtime=runtime
        )
    else:
        return parse_text_to_customer(
            text=content,
            product_id=product_id,
            auto_save=True,
            runtime=runtime
        )
