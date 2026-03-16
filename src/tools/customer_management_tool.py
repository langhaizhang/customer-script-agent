"""
客户资源管理工具
提供客户信息的增删改查、分类管理等功能
"""

from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client
from typing import Optional, List, Dict, Any
import json


@tool
def add_customer(
    name: str,
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
        
        customer_data = {
            "name": name,
            "customer_type": customer_type,
            "status": status
        }
        
        # 添加可选字段
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
        
        if response.data and isinstance(response.data, list) and len(response.data) > 0:
            customer_record: Dict[str, Any] = response.data[0]
            return f"✅ 成功添加客户：{name}\n客户ID: {customer_record['id']}"
        else:
            return "❌ 添加客户失败：未返回数据"
            
    except Exception as e:
        return f"❌ 添加客户时发生错误：{str(e)}"


@tool
def query_customers(
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
        
        customers_data: List[Dict[str, Any]] = response.data
        result = f"📋 找到 {len(customers_data)} 位客户：\n\n"
        
        for idx, customer in enumerate(customers_data, 1):
            tags_list = customer.get('tags', [])
            tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else "无"
            result += f"{idx}. 【{customer.get('name', '未知')}】\n"
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
        
        update_data = {}
        
        # 只更新提供的字段
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
        
        if response.data:
            return f"✅ 成功更新客户信息（ID: {customer_id}）"
        else:
            return f"❌ 未找到ID为 {customer_id} 的客户"
            
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
        
        if response.data:
            return f"✅ 成功删除客户（ID: {customer_id}）"
        else:
            return f"❌ 未找到ID为 {customer_id} 的客户"
            
    except Exception as e:
        return f"❌ 删除客户时发生错误：{str(e)}"


@tool
def classify_customer(
    customer_id: int,
    customer_type: str,
    runtime: ToolRuntime = None
) -> str:
    """
    对客户进行分类标记
    
    Args:
        customer_id: 客户ID（必填）
        customer_type: 客户类型（potential/interested/converted/churned）
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="classify_customer")
    
    try:
        client = get_supabase_client(ctx)
        
        # 验证客户类型
        valid_types = ["potential", "interested", "converted", "churned"]
        if customer_type not in valid_types:
            return f"❌ 无效的客户类型，必须是: {', '.join(valid_types)}"
        
        response = client.table('customers').update({"customer_type": customer_type}).eq('id', customer_id).execute()
        
        if response.data:
            type_names = {
                "potential": "潜在客户",
                "interested": "意向客户",
                "converted": "成交客户",
                "churned": "流失客户"
            }
            return f"✅ 成功将客户（ID: {customer_id}）分类为：{type_names.get(customer_type, customer_type)}"
        else:
            return f"❌ 未找到ID为 {customer_id} 的客户"
            
    except Exception as e:
        return f"❌ 分类客户时发生错误：{str(e)}"


@tool
def get_customer_statistics(
    runtime: ToolRuntime = None
) -> str:
    """
    获取客户统计数据
    
    Returns:
        客户统计信息
    """
    ctx = runtime.context if runtime else new_context(method="get_customer_statistics")
    
    try:
        client = get_supabase_client(ctx)
        
        # 获取所有客户
        response = client.table('customers').select('customer_type, status, industry').execute()
        
        if not response.data:
            return "暂无客户数据"
        
        customers: List[Dict[str, Any]] = response.data
        total = len(customers)
        
        # 统计各类型客户数量
        type_stats: Dict[str, int] = {}
        status_stats: Dict[str, int] = {}
        industry_stats: Dict[str, int] = {}
        
        for customer in customers:
            # 类型统计
            ctype = customer.get('customer_type', 'unknown')
            if isinstance(ctype, str):
                type_stats[ctype] = type_stats.get(ctype, 0) + 1
            
            # 状态统计
            status = customer.get('status', 'unknown')
            if isinstance(status, str):
                status_stats[status] = status_stats.get(status, 0) + 1
            
            # 行业统计
            industry = customer.get('industry', '未分类')
            if isinstance(industry, str):
                industry_stats[industry] = industry_stats.get(industry, 0) + 1
        
        # 格式化输出
        result = f"📊 客户资源统计报告\n\n"
        result += f"客户总数: {total}\n\n"
        
        result += "客户类型分布:\n"
        type_names = {
            "potential": "潜在客户",
            "interested": "意向客户",
            "converted": "成交客户",
            "churned": "流失客户"
        }
        for ctype, count in sorted(type_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  - {type_names.get(ctype, ctype)}: {count} ({percentage:.1f}%)\n"
        
        result += "\n客户状态分布:\n"
        status_names = {
            "active": "活跃",
            "inactive": "不活跃",
            "churned": "流失"
        }
        for status, count in sorted(status_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  - {status_names.get(status, status)}: {count} ({percentage:.1f}%)\n"
        
        result += "\n行业分布（Top 10）:\n"
        sorted_industries = sorted(industry_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        for industry, count in sorted_industries:
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  - {industry}: {count} ({percentage:.1f}%)\n"
        
        return result
        
    except Exception as e:
        return f"❌ 获取统计数据时发生错误：{str(e)}"
