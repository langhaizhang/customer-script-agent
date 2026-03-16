"""
对话收集工具
用于保存和管理与客户的对话记录
"""

from typing import Optional, List, Dict, Any, cast
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client
from datetime import datetime
import json


@tool
def save_conversation(
    customer_id: int,
    product_id: int,
    conversation_type: str = "phone",
    content: str = "",
    summary: Optional[str] = None,
    key_points: Optional[List[str]] = None,
    next_action: Optional[str] = None,
    sentiment: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    保存客户对话记录。
    
    记录与客户的沟通内容，包括电话、微信、邮件等形式的对话。
    可用于后续分析客户需求和跟进计划。
    
    Args:
        customer_id: 客户ID
        product_id: 产品ID
        conversation_type: 对话类型（phone/wechat/email/face_to_face/other）
        content: 对话内容详情
        summary: 对话摘要，可选
        key_points: 关键要点列表，可选
        next_action: 下一步行动，可选
        sentiment: 客户情绪（positive/neutral/negative）
    
    Returns:
        保存结果
    """
    ctx = runtime.context if runtime else new_context(method="save_conversation")
    
    try:
        db_client = get_supabase_client(ctx)
        
        # 构建对话数据
        conv_data: Dict[str, Any] = {
            "customer_id": customer_id,
            "product_id": product_id,
            "conversation_type": conversation_type,
            "content": content
        }
        
        if summary:
            conv_data["summary"] = summary
        if key_points:
            conv_data["key_points"] = key_points
        if next_action:
            conv_data["next_action"] = next_action
        if sentiment:
            conv_data["sentiment"] = sentiment
        
        # 保存到数据库
        response = db_client.table('conversations').insert(conv_data).execute()
        
        if response.data and len(response.data) > 0:
            conv = cast(Dict[str, Any], response.data[0])
            
            # 获取客户信息
            customer_response = db_client.table('customers').select('name, company').eq('id', customer_id).execute()
            customer_name = "未知客户"
            if customer_response.data and len(customer_response.data) > 0:
                customer = cast(Dict[str, Any], customer_response.data[0])
                customer_name = customer.get('name', '未知')
            
            type_names = {
                "phone": "电话",
                "wechat": "微信",
                "email": "邮件",
                "face_to_face": "面谈",
                "other": "其他"
            }
            
            result = f"""✅ 对话记录保存成功

📋 对话信息：
- 客户：{customer_name}
- 类型：{type_names.get(conversation_type, conversation_type)}
- 时间：{conv.get('created_at', '')}
- 对话ID：{conv.get('id')}"""
            
            if summary:
                result += f"\n\n📝 摘要：{summary}"
            
            if key_points:
                result += "\n\n🔑 关键要点："
                for point in key_points:
                    result += f"\n  • {point}"
            
            if next_action:
                result += f"\n\n📌 下一步：{next_action}"
            
            if sentiment:
                sentiment_emoji = {"positive": "😊", "neutral": "😐", "negative": "😟"}
                result += f"\n\n{sentiment_emoji.get(sentiment, '')} 客户情绪：{sentiment}"
            
            return result
        else:
            return "❌ 保存对话记录失败：未返回数据"
            
    except Exception as e:
        return f"❌ 保存对话记录时发生错误：{str(e)}"


@tool
def query_conversations(
    customer_id: Optional[int] = None,
    product_id: Optional[int] = None,
    conversation_type: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = 20,
    runtime: ToolRuntime = None
) -> str:
    """
    查询对话记录。
    
    根据条件筛选查询客户对话记录。
    
    Args:
        customer_id: 客户ID，可选
        product_id: 产品ID，可选
        conversation_type: 对话类型，可选
        sentiment: 客户情绪，可选
        limit: 返回数量限制，默认20
    
    Returns:
        对话记录列表
    """
    ctx = runtime.context if runtime else new_context(method="query_conversations")
    
    try:
        db_client = get_supabase_client(ctx)
        
        query = db_client.table('conversations').select('*, customers(name, company)')
        
        if customer_id:
            query = query.eq('customer_id', customer_id)
        if product_id:
            query = query.eq('product_id', product_id)
        if conversation_type:
            query = query.eq('conversation_type', conversation_type)
        if sentiment:
            query = query.eq('sentiment', sentiment)
        
        response = query.order('created_at', desc=True).limit(limit).execute()
        
        conversations = response.data or []
        
        if not conversations:
            return "📋 暂无对话记录"
        
        type_names = {
            "phone": "电话",
            "wechat": "微信",
            "email": "邮件",
            "face_to_face": "面谈",
            "other": "其他"
        }
        
        sentiment_emoji = {"positive": "😊", "neutral": "😐", "negative": "😟"}
        
        result = f"📋 共找到 {len(conversations)} 条对话记录\n\n"
        result += "━" * 50 + "\n"
        
        for conv_item in conversations:
            conv_dict = cast(Dict[str, Any], conv_item)
            customer = conv_dict.get('customers') or {}
            customer_dict = cast(Dict[str, Any], customer) if customer else {}
            result += f"\n【对话ID：{conv_dict.get('id')}】\n"
            result += f"👤 客户：{customer_dict.get('name', '未知')} ({customer_dict.get('company', '未知公司')})\n"
            result += f"📞 类型：{type_names.get(conv_dict.get('conversation_type'), conv_dict.get('conversation_type', '未知'))}\n"
            result += f"📅 时间：{conv_dict.get('created_at', '')}\n"
            
            if conv_dict.get('summary'):
                result += f"📝 摘要：{conv_dict.get('summary')}\n"
            
            if conv_dict.get('sentiment'):
                result += f"{sentiment_emoji.get(conv_dict.get('sentiment'), '')} 情绪：{conv_dict.get('sentiment')}\n"
            
            if conv_dict.get('next_action'):
                result += f"📌 下一步：{conv_dict.get('next_action')}\n"
            
            result += "━" * 50 + "\n"
        
        return result
            
    except Exception as e:
        return f"❌ 查询对话记录失败：{str(e)}"


@tool
def get_conversation(
    conversation_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    获取单条对话详情。
    
    Args:
        conversation_id: 对话ID
    
    Returns:
        对话详细信息
    """
    ctx = runtime.context if runtime else new_context(method="get_conversation")
    
    try:
        db_client = get_supabase_client(ctx)
        
        response = db_client.table('conversations').select('*, customers(name, company, phone, email)').eq('id', conversation_id).execute()
        
        if not response.data or len(response.data) == 0:
            return f"❌ 未找到对话ID {conversation_id}"
        
        conv = cast(Dict[str, Any], response.data[0])
        customer = conv.get('customers') or {}
        
        type_names = {
            "phone": "电话",
            "wechat": "微信",
            "email": "邮件",
            "face_to_face": "面谈",
            "other": "其他"
        }
        
        sentiment_emoji = {"positive": "😊", "neutral": "😐", "negative": "😟"}
        
        result = f"""📋 对话详情

━━━━━━━━━━━━━━━━━━━━━━━━━━

【基本信息】
对话ID：{conv.get('id')}
类型：{type_names.get(conv.get('conversation_type'), conv.get('conversation_type', '未知'))}
时间：{conv.get('created_at', '')}

【客户信息】
姓名：{customer.get('name', '未知')}
公司：{customer.get('company', '未知')}
电话：{customer.get('phone', '未知')}
邮箱：{customer.get('email', '未知')}

━━━━━━━━━━━━━━━━━━━━━━━━━━

【对话内容】
{conv.get('content', '暂无详细内容')}

━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        if conv.get('summary'):
            result += f"\n\n📝 摘要：{conv.get('summary')}"
        
        if conv.get('key_points'):
            result += "\n\n🔑 关键要点："
            for point in conv.get('key_points', []):
                result += f"\n  • {point}"
        
        if conv.get('next_action'):
            result += f"\n\n📌 下一步行动：{conv.get('next_action')}"
        
        if conv.get('sentiment'):
            result += f"\n\n{sentiment_emoji.get(conv.get('sentiment'), '')} 客户情绪：{conv.get('sentiment')}"
        
        return result
            
    except Exception as e:
        return f"❌ 获取对话详情失败：{str(e)}"


@tool
def analyze_customer_conversations(
    customer_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    分析客户对话历史。
    
    汇总分析某客户的所有对话记录，提取关键洞察。
    
    Args:
        customer_id: 客户ID
    
    Returns:
        分析结果
    """
    ctx = runtime.context if runtime else new_context(method="analyze_customer_conversations")
    
    try:
        db_client = get_supabase_client(ctx)
        
        # 获取客户信息
        customer_response = db_client.table('customers').select('*').eq('id', customer_id).execute()
        if not customer_response.data or len(customer_response.data) == 0:
            return f"❌ 未找到客户ID {customer_id}"
        
        customer = cast(Dict[str, Any], customer_response.data[0])
        
        # 获取该客户所有对话
        conv_response = db_client.table('conversations').select('*').eq('customer_id', customer_id).order('created_at', desc=True).execute()
        conversations = conv_response.data or []
        
        if not conversations:
            return f"📋 客户 {customer.get('name')} 暂无对话记录"
        
        # 统计分析
        type_counts: Dict[str, int] = {}
        sentiment_counts: Dict[str, int] = {}
        all_key_points: List[str] = []
        
        for conv_item in conversations:
            conv_dict = cast(Dict[str, Any], conv_item)
            conv_type = conv_dict.get('conversation_type', 'other') or 'other'
            type_counts[conv_type] = type_counts.get(conv_type, 0) + 1
            
            sentiment = conv_dict.get('sentiment')
            if sentiment:
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            if conv_dict.get('key_points'):
                key_pts = conv_dict.get('key_points', [])
                if isinstance(key_pts, list):
                    all_key_points.extend(key_pts)
        
        # 格式化输出
        type_names = {
            "phone": "电话",
            "wechat": "微信",
            "email": "邮件",
            "face_to_face": "面谈",
            "other": "其他"
        }
        
        result = f"""📊 客户对话分析报告

━━━━━━━━━━━━━━━━━━━━━━━━━━

【客户信息】
姓名：{customer.get('name')}
公司：{customer.get('company', '未知')}
类型：{customer.get('customer_type', '未知')}
状态：{customer.get('status', '未知')}

【沟通统计】
总对话次数：{len(conversations)} 次
最近联系：{cast(Dict[str, Any], conversations[0]).get('created_at', '未知') if conversations else '无记录'}

沟通方式分布：
"""
        
        for conv_type, count in type_counts.items():
            result += f"  • {type_names.get(conv_type, conv_type)}：{count} 次\n"
        
        if sentiment_counts:
            result += "\n情绪分布：\n"
            sentiment_emoji = {"positive": "😊 积极", "neutral": "😐 中立", "negative": "😟 消极"}
            for sentiment, count in sentiment_counts.items():
                result += f"  • {sentiment_emoji.get(sentiment, sentiment)}：{count} 次\n"
        
        if all_key_points:
            # 去重并统计频率
            point_counts: Dict[str, int] = {}
            for point in all_key_points:
                point_counts[point] = point_counts.get(point, 0) + 1
            
            sorted_points = sorted(point_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            result += "\n【高频关注点】\n"
            for point, count in sorted_points:
                result += f"  • {point}（{count}次）\n"
        
        # 最近对话摘要
        result += "\n【最近3次对话】\n"
        for i, conv_item in enumerate(conversations[:3], 1):
            conv_dict = cast(Dict[str, Any], conv_item)
            result += f"\n{i}. {type_names.get(conv_dict.get('conversation_type'), '未知')} - {str(conv_dict.get('created_at', ''))[:10]}\n"
            if conv_dict.get('summary'):
                result += f"   {conv_dict.get('summary')}\n"
            if conv_dict.get('next_action'):
                result += f"   📌 下一步：{conv_dict.get('next_action')}\n"
        
        return result
            
    except Exception as e:
        return f"❌ 分析对话失败：{str(e)}"


@tool
def update_conversation(
    conversation_id: int,
    summary: Optional[str] = None,
    key_points: Optional[List[str]] = None,
    next_action: Optional[str] = None,
    sentiment: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    更新对话记录。
    
    更新对话的摘要、关键要点、下一步行动或情绪标签。
    
    Args:
        conversation_id: 对话ID
        summary: 对话摘要，可选
        key_points: 关键要点列表，可选
        next_action: 下一步行动，可选
        sentiment: 客户情绪，可选
    
    Returns:
        更新结果
    """
    ctx = runtime.context if runtime else new_context(method="update_conversation")
    
    try:
        db_client = get_supabase_client(ctx)
        
        # 构建更新数据
        update_data: Dict[str, Any] = {}
        
        if summary is not None:
            update_data["summary"] = summary
        if key_points is not None:
            update_data["key_points"] = key_points
        if next_action is not None:
            update_data["next_action"] = next_action
        if sentiment is not None:
            update_data["sentiment"] = sentiment
        
        if not update_data:
            return "❌ 请提供至少一个要更新的字段"
        
        # 执行更新
        response = db_client.table('conversations').update(update_data).eq('id', conversation_id).execute()
        
        if response.data and len(response.data) > 0:
            return f"✅ 对话记录已更新，ID: {conversation_id}"
        else:
            return f"❌ 更新失败：未找到对话ID {conversation_id}"
            
    except Exception as e:
        return f"❌ 更新对话记录失败：{str(e)}"
