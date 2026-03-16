"""
客户资源管理工具
提供客户信息的增删改查、分类管理等功能
支持多产品/业务线管理
"""

from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client
from typing import Optional, List, Dict, Any, cast
import json


@tool
def add_customer(
    name: str,
    product_id: Optional[int] = None,
    company: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: str = "potential",
    status: str = "active",
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
    source: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    添加新客户到客户资源库
    
    Args:
        name: 客户姓名（必填）
        product_id: 关联的产品ID，可选
        company: 公司名称
        phone: 联系电话
        email: 邮箱地址
        industry: 所属行业
        customer_type: 客户类型（potential/interested/converted/churned）
        status: 客户状态（active/inactive/churned）
        tags: 客户标签列表
        notes: 备注信息
        source: 客户来源
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="add_customer")
    
    try:
        client = get_supabase_client(ctx)
        
        customer_data: Dict[str, Any] = {
            "name": name,
            "customer_type": customer_type,
            "status": status
        }
        
        # 添加可选字段
        if product_id:
            customer_data["product_id"] = product_id
        if company:
            customer_data["company"] = company
        if phone:
            customer_data["phone"] = phone
        if email:
            customer_data["email"] = email
        if industry:
            customer_data["industry"] = industry
        if tags:
            customer_data["tags"] = tags
        if notes:
            customer_data["notes"] = notes
        if source:
            customer_data["source"] = source
        
        response = client.table('customers').insert(customer_data).execute()
        
        if response.data and len(response.data) > 0:
            customer = cast(Dict[str, Any], response.data[0])
            return f"✅ 成功添加客户：{name}\n客户ID: {customer.get('id')}"
        else:
            return "❌ 添加客户失败：未返回数据"
            
    except Exception as e:
        return f"❌ 添加客户时发生错误：{str(e)}"


@tool
def query_customers(
    product_id: Optional[int] = None,
    name: Optional[str] = None,
    company: Optional[str] = None,
    customer_type: Optional[str] = None,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    limit: int = 20,
    runtime: ToolRuntime = None
) -> str:
    """
    查询客户资源信息
    
    Args:
        product_id: 产品ID筛选
        name: 客户姓名（模糊搜索）
        company: 公司名称（模糊搜索）
        customer_type: 客户类型筛选
        status: 客户状态筛选
        industry: 行业筛选
        limit: 返回结果数量限制（默认20条）
    
    Returns:
        客户信息列表
    """
    ctx = runtime.context if runtime else new_context(method="query_customers")
    
    try:
        client = get_supabase_client(ctx)
        
        query = client.table('customers').select('*')
        
        # 添加筛选条件
        if product_id:
            query = query.eq('product_id', product_id)
        if name:
            query = query.ilike('name', f'%{name}%')
        if company:
            query = query.ilike('company', f'%{company}%')
        if customer_type:
            query = query.eq('customer_type', customer_type)
        if status:
            query = query.eq('status', status)
        if industry:
            query = query.eq('industry', industry)
        
        response = query.limit(limit).order('created_at', desc=True).execute()
        
        if not response.data:
            return "未找到匹配的客户信息"
        
        customers_data = cast(List[Dict[str, Any]], response.data)
        result = f"📋 找到 {len(customers_data)} 位客户：\n\n"
        
        for idx, customer in enumerate(customers_data, 1):
            tags_list = customer.get('tags', [])
            tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else "无"
            result += f"{idx}. 【{customer.get('name', '未知')}】\n"
            result += f"   - 产品ID: {customer.get('product_id', '未关联')}\n"
            result += f"   - 公司: {customer.get('company', '未知')}\n"
            result += f"   - 电话: {customer.get('phone', '未知')}\n"
            result += f"   - 邮箱: {customer.get('email', '未知')}\n"
            result += f"   - 行业: {customer.get('industry', '未知')}\n"
            result += f"   - 类型: {customer.get('customer_type', '未知')}\n"
            result += f"   - 状态: {customer.get('status', '未知')}\n"
            result += f"   - 标签: {tags_str}\n"
            result += f"   - 来源: {customer.get('source', '未知')}\n"
            result += f"   - 备注: {customer.get('notes', '无')}\n"
            result += f"   - 创建时间: {customer.get('created_at', '未知')}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ 查询客户时发生错误：{str(e)}"


@tool
def update_customer(
    customer_id: int,
    product_id: Optional[int] = None,
    name: Optional[str] = None,
    company: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
    source: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    更新客户信息
    
    Args:
        customer_id: 客户ID（必填）
        product_id: 关联的产品ID，可选
        name: 客户姓名
        company: 公司名称
        phone: 联系电话
        email: 邮箱地址
        industry: 所属行业
        customer_type: 客户类型
        status: 客户状态
        tags: 客户标签列表
        notes: 备注信息
        source: 客户来源
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="update_customer")
    
    try:
        client = get_supabase_client(ctx)
        
        update_data: Dict[str, Any] = {}
        
        # 只更新提供的字段
        if product_id is not None:
            update_data["product_id"] = product_id
        if name is not None:
            update_data["name"] = name
        if company is not None:
            update_data["company"] = company
        if phone is not None:
            update_data["phone"] = phone
        if email is not None:
            update_data["email"] = email
        if industry is not None:
            update_data["industry"] = industry
        if customer_type is not None:
            update_data["customer_type"] = customer_type
        if status is not None:
            update_data["status"] = status
        if tags is not None:
            update_data["tags"] = tags
        if notes is not None:
            update_data["notes"] = notes
        if source is not None:
            update_data["source"] = source
        
        if not update_data:
            return "❌ 未提供任何需要更新的字段"
        
        response = client.table('customers').update(update_data).eq('id', customer_id).execute()
        
        if response.data and len(response.data) > 0:
            return f"✅ 客户信息更新成功，客户ID: {customer_id}"
        else:
            return f"❌ 未找到ID为 {customer_id} 的客户或更新失败"
            
    except Exception as e:
        return f"❌ 更新客户时发生错误：{str(e)}"


@tool
def delete_customer(
    customer_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    删除客户信息
    
    Args:
        customer_id: 客户ID（必填）
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="delete_customer")
    
    try:
        client = get_supabase_client(ctx)
        
        response = client.table('customers').delete().eq('id', customer_id).execute()
        
        if response.data and len(response.data) > 0:
            return f"✅ 客户已删除，客户ID: {customer_id}"
        else:
            return f"❌ 未找到ID为 {customer_id} 的客户或删除失败"
            
    except Exception as e:
        return f"❌ 删除客户时发生错误：{str(e)}"


@tool
def classify_customer(
    customer_id: int,
    customer_type: str,
    runtime: ToolRuntime = None
) -> str:
    """
    对客户进行分类
    
    Args:
        customer_id: 客户ID（必填）
        customer_type: 客户类型（potential/interested/converted/churned）
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="classify_customer")
    
    try:
        client = get_supabase_client(ctx)
        
        response = client.table('customers').update({"customer_type": customer_type}).eq('id', customer_id).execute()
        
        if response.data and len(response.data) > 0:
            return f"✅ 客户分类已更新为：{customer_type}"
        else:
            return f"❌ 未找到ID为 {customer_id} 的客户或更新失败"
            
    except Exception as e:
        return f"❌ 客户分类时发生错误：{str(e)}"


@tool
def get_customer_statistics(
    product_id: Optional[int] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    获取客户统计数据
    
    Args:
        product_id: 产品ID，可选。不传则统计全部客户
    
    Returns:
        客户统计信息
    """
    ctx = runtime.context if runtime else new_context(method="get_customer_statistics")
    
    try:
        client = get_supabase_client(ctx)
        
        # 构建查询
        query = client.table('customers').select('customer_type, status, industry')
        if product_id:
            query = query.eq('product_id', product_id)
        
        response = query.execute()
        
        if not response.data:
            return "暂无客户数据"
        
        customers = cast(List[Dict[str, Any]], response.data)
        
        # 统计各类型客户数量
        type_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        industry_counts: Dict[str, int] = {}
        
        for customer in customers:
            # 客户类型统计
            ctype = str(customer.get('customer_type', 'unknown'))
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
            
            # 状态统计
            st = str(customer.get('status', 'unknown'))
            status_counts[st] = status_counts.get(st, 0) + 1
            
            # 行业统计
            ind = str(customer.get('industry', '未知'))
            industry_counts[ind] = industry_counts.get(ind, 0) + 1
        
        # 类型名称映射
        type_names: Dict[str, str] = {
            "potential": "潜在客户",
            "interested": "意向客户",
            "converted": "成交客户",
            "churned": "流失客户"
        }
        
        status_names: Dict[str, str] = {
            "active": "活跃",
            "inactive": "不活跃",
            "churned": "流失"
        }
        
        result = "📊 客户统计信息\n\n"
        result += "📋 客户类型分布：\n"
        for ctype, count in type_counts.items():
            result += f"  - {type_names.get(ctype, ctype)}: {count} 位\n"
        
        result += "\n📋 客户状态分布：\n"
        for status, count in status_counts.items():
            result += f"  - {status_names.get(status, status)}: {count} 位\n"
        
        result += "\n📋 行业分布：\n"
        for industry, count in sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            result += f"  - {industry}: {count} 位\n"
        
        result += f"\n总计：{len(customers)} 位客户"
        
        return result
        
    except Exception as e:
        return f"❌ 获取统计数据时发生错误：{str(e)}"
