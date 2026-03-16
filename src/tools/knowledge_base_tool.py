"""
资料库管理工具模块

提供产品/业务资料的管理功能，支持资料的分类、检索和智能应用。
"""

from typing import Optional, List, Dict, Any, cast
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client

# 资料分类映射
CATEGORY_NAMES: Dict[str, str] = {
    "product_intro": "产品介绍",
    "faq": "常见问题",
    "competitive": "竞品分析",
    "advantage": "核心优势",
    "use_case": "使用案例",
    "general": "通用资料"
}


@tool
def add_knowledge(
    product_id: int,
    title: str,
    content: str,
    category: str = "general",
    tags: str = "",
    source: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    添加产品/业务资料。
    
    Args:
        product_id: 关联的产品ID，必填
        title: 资料标题，必填
        content: 资料内容，必填
        category: 资料分类，可选值：product_intro(产品介绍), faq(常见问题), competitive(竞品分析), advantage(核心优势), use_case(使用案例), general(通用资料)
        tags: 标签，多个用逗号分隔
        source: 资料来源
    
    Returns:
        添加结果
    """
    ctx = runtime.context if runtime else new_context(method="add_knowledge")
    
    try:
        client = get_supabase_client(ctx)
        
        # 检查产品是否存在
        product_response = client.table('products').select('name').eq('id', product_id).execute()
        if not product_response.data or len(product_response.data) == 0:
            return f"❌ 未找到ID为 {product_id} 的产品"
        
        # 处理标签
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        
        knowledge_data: Dict[str, Any] = {
            "product_id": product_id,
            "title": title,
            "content": content,
            "category": category
        }
        
        if tag_list:
            knowledge_data["tags"] = tag_list
        if source:
            knowledge_data["source"] = source
        
        response = client.table('knowledge_base').insert(knowledge_data).execute()
        
        if response.data and len(response.data) > 0:
            prod = cast(Dict[str, Any], product_response.data[0])
            product_name = str(prod.get('name', '未知'))
            
            kd = cast(Dict[str, Any], response.data[0])
            return f"""✅ 资料添加成功

📋 资料信息：
- ID: {kd.get('id')}
- 产品: {product_name}
- 标题: {title}
- 分类: {CATEGORY_NAMES.get(category, category)}
- 标签: {', '.join(tag_list) if tag_list else '无'}
- 内容长度: {len(content)} 字符"""
            
    except Exception as e:
        return f"❌ 添加资料失败: {str(e)}"


@tool
def query_knowledge(
    product_id: int = 0,
    category: str = "",
    keyword: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    查询资料列表。
    
    Args:
        product_id: 产品ID，0或空表示查询所有产品的资料
        category: 分类筛选
        keyword: 关键词搜索，匹配标题或内容
    
    Returns:
        资料列表
    """
    ctx = runtime.context if runtime else new_context(method="query_knowledge")
    
    try:
        client = get_supabase_client(ctx)
        
        query = client.table('knowledge_base').select('*')
        
        if product_id and product_id > 0:
            query = query.eq('product_id', product_id)
        
        if category:
            query = query.eq('category', category)
        
        response = query.order('created_at', desc=True).limit(50).execute()
        
        knowledge_list = cast(List[Dict[str, Any]], response.data if response.data else [])
        
        # 关键词过滤
        if keyword:
            kw = keyword.lower()
            knowledge_list = [k for k in knowledge_list if 
                            kw in str(k.get('title', '')).lower() or 
                            kw in str(k.get('content', '')).lower()]
        
        if not knowledge_list:
            return "📋 暂无资料数据"
        
        result = f"📋 资料列表（共 {len(knowledge_list)} 条）\n\n"
        
        # 获取产品名称映射
        product_ids = list(set(k.get('product_id') for k in knowledge_list if k.get('product_id')))
        product_names: Dict[int, str] = {}
        if product_ids:
            products_response = client.table('products').select('id, name').in_('id', product_ids).execute()
            if products_response.data:
                for p in products_response.data:
                    prod = cast(Dict[str, Any], p)
                    product_names[int(prod.get('id', 0))] = str(prod.get('name', '未知'))
        
        for k in knowledge_list:
            pid = k.get('product_id')
            product_name = product_names.get(pid, '未知产品') if pid else '未知产品'
            content = str(k.get('content', ''))
            content_preview = content[:100] + "..." if len(content) > 100 else content
            content_preview = content_preview.replace('\n', ' ')
            cat = str(k.get('category', 'general'))
            created = str(k.get('created_at', ''))
            
            result += f"""┌─────────────────────────────
│ ID: {k.get('id')} | 产品: {product_name}
│ 标题: {k.get('title')}
│ 分类: {CATEGORY_NAMES.get(cat, cat)}
│ 内容预览: {content_preview}
│ 创建时间: {created[:16].replace('T', ' ')}
└─────────────────────────────\n\n"""
        
        return result
            
    except Exception as e:
        return f"❌ 查询资料失败: {str(e)}"


@tool
def get_knowledge(
    knowledge_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    获取单条资料详情。
    
    Args:
        knowledge_id: 资料ID
    
    Returns:
        资料详情
    """
    ctx = runtime.context if runtime else new_context(method="get_knowledge")
    
    try:
        client = get_supabase_client(ctx)
        
        response = client.table('knowledge_base').select('*').eq('id', knowledge_id).execute()
        
        if not response.data or len(response.data) == 0:
            return f"❌ 未找到ID为 {knowledge_id} 的资料"
        
        knowledge = cast(Dict[str, Any], response.data[0])
        
        # 获取产品名称
        product_name = "未知产品"
        if knowledge.get('product_id'):
            product_response = client.table('products').select('name').eq('id', knowledge['product_id']).execute()
            if product_response.data:
                prod = cast(Dict[str, Any], product_response.data[0])
                product_name = str(prod.get('name', '未知'))
        
        tags = knowledge.get('tags', [])
        tags_str = ', '.join(tags) if isinstance(tags, list) and tags else '无'
        cat = str(knowledge.get('category', 'general'))
        created = str(knowledge.get('created_at', ''))
        
        return f"""📋 资料详情

┌─────────────────────────────
│ ID: {knowledge.get('id')}
│ 产品: {product_name}
│ 标题: {knowledge.get('title')}
│ 分类: {CATEGORY_NAMES.get(cat, cat)}
│ 标签: {tags_str}
│ 来源: {str(knowledge.get('source') or '未知')}
│ 创建时间: {created[:19].replace('T', ' ')}
└─────────────────────────────

📄 内容：
{knowledge.get('content', '')}"""
            
    except Exception as e:
        return f"❌ 获取资料失败: {str(e)}"


@tool
def update_knowledge(
    knowledge_id: int,
    title: str = "",
    content: str = "",
    category: str = "",
    tags: str = "",
    source: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    更新资料信息。
    
    Args:
        knowledge_id: 资料ID，必填
        title: 新标题，可选
        content: 新内容，可选
        category: 新分类，可选
        tags: 新标签，多个用逗号分隔
        source: 新来源，可选
    
    Returns:
        更新结果
    """
    ctx = runtime.context if runtime else new_context(method="update_knowledge")
    
    try:
        client = get_supabase_client(ctx)
        
        update_data: Dict[str, Any] = {}
        
        if title:
            update_data["title"] = title
        if content:
            update_data["content"] = content
        if category:
            update_data["category"] = category
        if tags:
            update_data["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
        if source:
            update_data["source"] = source
        
        if not update_data:
            return "❌ 未提供任何需要更新的字段"
        
        response = client.table('knowledge_base').update(update_data).eq('id', knowledge_id).execute()
        
        if response.data and len(response.data) > 0:
            knowledge = cast(Dict[str, Any], response.data[0])
            cat = str(knowledge.get('category', 'general'))
            return f"""✅ 资料更新成功

📋 更新后的信息：
- ID: {knowledge.get('id')}
- 标题: {knowledge.get('title')}
- 分类: {CATEGORY_NAMES.get(cat, cat)}"""
        else:
            return f"❌ 未找到ID为 {knowledge_id} 的资料"
            
    except Exception as e:
        return f"❌ 更新资料失败: {str(e)}"


@tool
def delete_knowledge(
    knowledge_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    删除资料。
    
    Args:
        knowledge_id: 资料ID
    
    Returns:
        删除结果
    """
    ctx = runtime.context if runtime else new_context(method="delete_knowledge")
    
    try:
        client = get_supabase_client(ctx)
        
        # 先获取资料信息
        response = client.table('knowledge_base').select('title').eq('id', knowledge_id).execute()
        
        if not response.data or len(response.data) == 0:
            return f"❌ 未找到ID为 {knowledge_id} 的资料"
        
        kd = cast(Dict[str, Any], response.data[0])
        title = str(kd.get('title', '未知'))
        
        # 删除
        client.table('knowledge_base').delete().eq('id', knowledge_id).execute()
        
        return f"""✅ 资料已删除

📋 删除的资料：{title}（ID: {knowledge_id}）"""
            
    except Exception as e:
        return f"❌ 删除资料失败: {str(e)}"


@tool
def get_knowledge_for_script(
    product_id: int,
    scenario: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    获取用于话术生成的产品资料。
    
    根据话术使用场景，智能检索相关的产品资料，用于辅助话术生成。
    
    Args:
        product_id: 产品ID
        scenario: 使用场景描述，如"首次联系客户"、"处理价格异议"等
    
    Returns:
        相关资料内容
    """
    ctx = runtime.context if runtime else new_context(method="get_knowledge_for_script")
    
    try:
        client = get_supabase_client(ctx)
        
        # 获取产品信息
        product_response = client.table('products').select('name').eq('id', product_id).execute()
        if not product_response.data or len(product_response.data) == 0:
            return f"❌ 未找到ID为 {product_id} 的产品"
        
        prod = cast(Dict[str, Any], product_response.data[0])
        product_name = str(prod.get('name', '未知'))
        
        # 获取该产品的所有资料
        response = client.table('knowledge_base').select('*').eq('product_id', product_id).execute()
        knowledge_list = cast(List[Dict[str, Any]], response.data if response.data else [])
        
        if not knowledge_list:
            return f"📋 产品「{product_name}」暂无资料，建议先添加产品资料"
        
        result = f"""📚 产品「{product_name}」资料汇总

"""
        # 按分类组织资料
        categories: Dict[str, List[Dict[str, Any]]] = {}
        for k in knowledge_list:
            cat = str(k.get('category', 'general'))
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(k)
        
        for cat, items in categories.items():
            result += f"\n## {CATEGORY_NAMES.get(cat, cat)}\n\n"
            for item in items:
                result += f"### {item.get('title', '未知')}\n{item.get('content', '')}\n\n"
        
        return result
            
    except Exception as e:
        return f"❌ 获取资料失败: {str(e)}"


@tool
def get_product_knowledge_summary(
    product_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    获取产品资料统计概览。
    
    Args:
        product_id: 产品ID
    
    Returns:
        资料统计信息
    """
    ctx = runtime.context if runtime else new_context(method="get_product_knowledge_summary")
    
    try:
        client = get_supabase_client(ctx)
        
        # 获取产品信息
        product_response = client.table('products').select('name').eq('id', product_id).execute()
        if not product_response.data or len(product_response.data) == 0:
            return f"❌ 未找到ID为 {product_id} 的产品"
        
        prod = cast(Dict[str, Any], product_response.data[0])
        product_name = str(prod.get('name', '未知'))
        
        # 获取资料
        response = client.table('knowledge_base').select('category').eq('product_id', product_id).execute()
        knowledge_list = cast(List[Dict[str, Any]], response.data if response.data else [])
        
        total = len(knowledge_list)
        categories: Dict[str, int] = {}
        for k in knowledge_list:
            cat = str(k.get('category', 'general'))
            categories[cat] = categories.get(cat, 0) + 1
        
        result = f"""📊 产品「{product_name}」资料统计

┌─────────────────────────────
│ 总资料数: {total} 条
└─────────────────────────────

"""
        for cat, count in categories.items():
            result += f"• {CATEGORY_NAMES.get(cat, cat)}: {count} 条\n"
        
        return result
            
    except Exception as e:
        return f"❌ 获取统计失败: {str(e)}"
