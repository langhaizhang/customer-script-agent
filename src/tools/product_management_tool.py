"""
产品/业务管理工具模块

提供产品的增删改查功能，支持多产品/业务线管理。
"""

from typing import Optional, List, Dict, Any, cast
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client


@tool
def create_product(
    name: str,
    description: str = "",
    icon: str = "",
    color: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    创建新产品/业务线。
    
    Args:
        name: 产品/业务名称，必填
        description: 产品/业务描述，可选
        icon: 图标标识，可选
        color: 主题颜色，可选，如 #1890ff
    
    Returns:
        创建结果，包含产品ID和详细信息
    """
    ctx = runtime.context if runtime else new_context(method="create_product")
    
    try:
        client = get_supabase_client(ctx)
        
        product_data: Dict[str, Any] = {
            "name": name,
            "status": "active"
        }
        
        if description:
            product_data["description"] = description
        if icon:
            product_data["icon"] = icon
        if color:
            product_data["color"] = color
        
        response = client.table('products').insert(product_data).execute()
        
        if response.data and len(response.data) > 0:
            product = cast(Dict[str, Any], response.data[0])
            desc_val = product.get('description', '暂无') or '暂无'
            return f"""✅ 产品创建成功

📋 产品信息：
- ID: {product['id']}
- 名称: {product['name']}
- 描述: {desc_val}
- 状态: {product['status']}
- 创建时间: {str(product['created_at'])[:19].replace('T', ' ')}"""
            
    except Exception as e:
        return f"❌ 创建产品失败: {str(e)}"


@tool
def query_products(
    status: str = "",
    keyword: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    查询产品/业务列表。
    
    Args:
        status: 状态筛选，可选值：active(活跃), inactive(停用)，默认查询全部
        keyword: 关键词搜索，匹配产品名称或描述
    
    Returns:
        产品列表
    """
    ctx = runtime.context if runtime else new_context(method="query_products")
    
    try:
        client = get_supabase_client(ctx)
        
        query = client.table('products').select('*')
        
        if status:
            query = query.eq('status', status)
        
        response = query.order('created_at', desc=True).execute()
        
        products = cast(List[Dict[str, Any]], response.data if response.data else [])
        
        # 如果有关键词，在Python中进行过滤
        if keyword:
            kw = keyword.lower()
            products = [p for p in products if 
                       kw in str(p.get('name', '')).lower() or 
                       kw in str(p.get('description', '')).lower()]
        
        if not products:
            return "📋 暂无产品数据"
        
        result = f"📋 产品列表（共 {len(products)} 个）\n\n"
        for p in products:
            desc = str(p.get('description', '暂无') or '暂无')
            desc_preview = desc[:50] + '...' if len(desc) > 50 else desc
            st = str(p.get('status', 'active'))
            status_icon = '🟢' if st == 'active' else '🔴'
            created = str(p.get('created_at', ''))
            
            result += f"""┌─────────────────────────────
│ ID: {p.get('id')}
│ 名称: {p.get('name')}
│ 描述: {desc_preview}
│ 状态: {status_icon} {'活跃' if st == 'active' else '停用'}
│ 创建时间: {created[:16].replace('T', ' ')}
└─────────────────────────────\n\n"""
        
        return result
            
    except Exception as e:
        return f"❌ 查询产品失败: {str(e)}"


@tool
def get_product(
    product_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    获取单个产品详细信息。
    
    Args:
        product_id: 产品ID
    
    Returns:
        产品详细信息
    """
    ctx = runtime.context if runtime else new_context(method="get_product")
    
    try:
        client = get_supabase_client(ctx)
        
        response = client.table('products').select('*').eq('id', product_id).execute()
        
        if not response.data or len(response.data) == 0:
            return f"❌ 未找到ID为 {product_id} 的产品"
        
        product = cast(Dict[str, Any], response.data[0])
        st = str(product.get('status', 'active'))
        status_icon = '🟢' if st == 'active' else '🔴'
        updated = str(product.get('updated_at', ''))
        desc = str(product.get('description', '暂无') or '暂无')
        
        return f"""📋 产品详情

┌─────────────────────────────
│ ID: {product.get('id')}
│ 名称: {product.get('name')}
│ 描述: {desc}
│ 图标: {str(product.get('icon') or '未设置')}
│ 颜色: {str(product.get('color') or '未设置')}
│ 状态: {status_icon} {'活跃' if st == 'active' else '停用'}
│ 创建时间: {str(product.get('created_at', ''))[:19].replace('T', ' ')}
│ 更新时间: {updated[:19].replace('T', ' ') if updated else '未更新'}
└─────────────────────────────"""
            
    except Exception as e:
        return f"❌ 获取产品信息失败: {str(e)}"


@tool
def update_product(
    product_id: int,
    name: str = "",
    description: str = "",
    icon: str = "",
    color: str = "",
    status: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    更新产品/业务信息。
    
    Args:
        product_id: 产品ID，必填
        name: 新的产品名称，可选
        description: 新的产品描述，可选
        icon: 新的图标标识，可选
        color: 新的主题颜色，可选
        status: 新的状态，可选值：active, inactive
    
    Returns:
        更新结果
    """
    ctx = runtime.context if runtime else new_context(method="update_product")
    
    try:
        client = get_supabase_client(ctx)
        
        update_data: Dict[str, Any] = {}
        
        if name:
            update_data["name"] = name
        if description:
            update_data["description"] = description
        if icon:
            update_data["icon"] = icon
        if color:
            update_data["color"] = color
        if status:
            update_data["status"] = status
        
        if not update_data:
            return "❌ 未提供任何需要更新的字段"
        
        response = client.table('products').update(update_data).eq('id', product_id).execute()
        
        if response.data and len(response.data) > 0:
            product = cast(Dict[str, Any], response.data[0])
            st = str(product.get('status', 'active'))
            status_icon = '🟢' if st == 'active' else '🔴'
            
            return f"""✅ 产品更新成功

📋 更新后的信息：
- ID: {product.get('id')}
- 名称: {product.get('name')}
- 状态: {status_icon} {'活跃' if st == 'active' else '停用'}"""
        else:
            return f"❌ 未找到ID为 {product_id} 的产品"
            
    except Exception as e:
        return f"❌ 更新产品失败: {str(e)}"


@tool
def delete_product(
    product_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    删除产品/业务。
    
    注意：删除产品后，关联的客户、话术、资料的 product_id 会被设为 NULL。
    
    Args:
        product_id: 产品ID
    
    Returns:
        删除结果
    """
    ctx = runtime.context if runtime else new_context(method="delete_product")
    
    try:
        client = get_supabase_client(ctx)
        
        # 先获取产品信息
        response = client.table('products').select('*').eq('id', product_id).execute()
        
        if not response.data or len(response.data) == 0:
            return f"❌ 未找到ID为 {product_id} 的产品"
        
        product = cast(Dict[str, Any], response.data[0])
        product_name = str(product.get('name', '未知'))
        
        # 删除产品
        client.table('products').delete().eq('id', product_id).execute()
        
        return f"""✅ 产品已删除

📋 删除的产品：{product_name}（ID: {product_id}）

⚠️ 注意：该产品关联的客户、话术、资料已解除关联（product_id 设为空）"""
            
    except Exception as e:
        return f"❌ 删除产品失败: {str(e)}"
