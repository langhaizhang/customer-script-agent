"""
话术库管理工具
提供话术的增删改查、智能推荐、AI生成等功能
支持多产品/业务线管理
"""

from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client
from typing import Optional, List, Dict, Any, cast
import json


@tool
def add_script(
    title: str,
    content: str,
    product_id: Optional[int] = None,
    category: str = "general",
    scenario: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    effectiveness_score: Optional[float] = None,
    is_ai_generated: bool = False,
    runtime: ToolRuntime = None
) -> str:
    """
    添加新话术到话术库
    
    Args:
        title: 话术标题（必填）
        content: 话术内容（必填）
        product_id: 关联的产品ID，可选
        category: 话术分类（opening/introduction/objection/closing/follow_up/general）
        scenario: 使用场景
        keywords: 关键词标签列表
        industry: 适用行业
        customer_type: 适用客户类型
        effectiveness_score: 有效性评分(0-10)
        is_ai_generated: 是否AI生成，默认False
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="add_script")
    
    try:
        client = get_supabase_client(ctx)
        
        script_data: Dict[str, Any] = {
            "title": title,
            "content": content,
            "category": category,
            "is_ai_generated": is_ai_generated
        }
        
        # 添加可选字段
        if product_id:
            script_data["product_id"] = product_id
        if scenario:
            script_data["scenario"] = scenario
        if keywords:
            script_data["keywords"] = keywords
        if industry:
            script_data["industry"] = industry
        if customer_type:
            script_data["customer_type"] = customer_type
        if effectiveness_score is not None:
            # 验证评分范围
            if 0 <= effectiveness_score <= 10:
                script_data["effectiveness_score"] = effectiveness_score
            else:
                return "❌ 有效性评分必须在 0-10 之间"
        
        # 保存到数据库
        response = client.table('scripts').insert(script_data).execute()
        
        if response.data and len(response.data) > 0:
            script = cast(Dict[str, Any], response.data[0])
            return f"✅ 成功添加话术：{title}\n话术ID: {script.get('id')}"
        else:
            return "❌ 添加话术失败：未返回数据"
            
    except Exception as e:
        return f"❌ 添加话术时发生错误：{str(e)}"


@tool
def query_scripts(
    product_id: Optional[int] = None,
    title: Optional[str] = None,
    category: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = 20,
    runtime: ToolRuntime = None
) -> str:
    """
    查询话术库信息
    
    Args:
        product_id: 产品ID筛选
        title: 话术标题（模糊搜索）
        category: 话术分类筛选
        industry: 适用行业筛选
        customer_type: 适用客户类型筛选
        min_score: 最低有效性评分筛选
        limit: 返回结果数量限制（默认20条）
    
    Returns:
        话术信息列表
    """
    ctx = runtime.context if runtime else new_context(method="query_scripts")
    
    try:
        client = get_supabase_client(ctx)
        
        query = client.table('scripts').select('*')
        
        # 添加筛选条件
        if product_id:
            query = query.eq('product_id', product_id)
        if title:
            query = query.ilike('title', f'%{title}%')
        if category:
            query = query.eq('category', category)
        if industry:
            query = query.eq('industry', industry)
        if customer_type:
            query = query.eq('customer_type', customer_type)
        if min_score is not None:
            query = query.gte('effectiveness_score', min_score)
        
        response = query.limit(limit).order('created_at', desc=True).execute()
        
        if not response.data:
            return "未找到匹配的话术信息"
        
        scripts_data = cast(List[Dict[str, Any]], response.data)
        
        # 分类名称映射
        category_names: Dict[str, str] = {
            "opening": "开场白",
            "introduction": "产品介绍",
            "objection": "异议处理",
            "closing": "成交话术",
            "follow_up": "跟进话术",
            "general": "通用话术"
        }
        
        result = f"📚 找到 {len(scripts_data)} 条话术：\n\n"
        
        for idx, script in enumerate(scripts_data, 1):
            keywords_list = script.get('keywords', [])
            keywords_str = ", ".join(keywords_list) if isinstance(keywords_list, list) else "无"
            score = script.get('effectiveness_score')
            score_str = f"{float(score):.1f}" if isinstance(score, (int, float)) else "未评分"
            ai_flag = "🤖" if script.get('is_ai_generated') else "👤"
            
            content_text = str(script.get('content', ''))
            content_preview = content_text[:100] if len(content_text) > 100 else content_text
            cat = str(script.get('category', 'general'))
            
            result += f"{idx}. {ai_flag}【{script.get('title', '未知')}】\n"
            result += f"   - 产品ID: {script.get('product_id', '未关联')}\n"
            result += f"   - 分类: {category_names.get(cat, cat)}\n"
            result += f"   - 内容: {content_preview}...\n"
            result += f"   - 使用场景: {script.get('scenario', '通用')}\n"
            result += f"   - 关键词: {keywords_str}\n"
            result += f"   - 有效性评分: {score_str}\n"
            result += f"   - 使用次数: {script.get('usage_count', 0)}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ 查询话术时发生错误：{str(e)}"


@tool
def update_script(
    script_id: int,
    product_id: Optional[int] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
    scenario: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    effectiveness_score: Optional[float] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    更新话术信息
    
    Args:
        script_id: 话术ID（必填）
        product_id: 关联的产品ID，可选
        title: 话术标题
        content: 话术内容
        category: 话术分类
        scenario: 使用场景
        keywords: 关键词标签列表
        industry: 适用行业
        customer_type: 适用客户类型
        effectiveness_score: 有效性评分(0-10)
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="update_script")
    
    try:
        client = get_supabase_client(ctx)
        
        update_data: Dict[str, Any] = {}
        
        # 只更新提供的字段
        if product_id is not None:
            update_data["product_id"] = product_id
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content
        if category is not None:
            update_data["category"] = category
        if scenario is not None:
            update_data["scenario"] = scenario
        if keywords is not None:
            update_data["keywords"] = keywords
        if industry is not None:
            update_data["industry"] = industry
        if customer_type is not None:
            update_data["customer_type"] = customer_type
        if effectiveness_score is not None:
            if 0 <= effectiveness_score <= 10:
                update_data["effectiveness_score"] = effectiveness_score
            else:
                return "❌ 有效性评分必须在 0-10 之间"
        
        if not update_data:
            return "❌ 未提供任何需要更新的字段"
        
        response = client.table('scripts').update(update_data).eq('id', script_id).execute()
        
        if response.data and len(response.data) > 0:
            return f"✅ 话术信息更新成功，话术ID: {script_id}"
        else:
            return f"❌ 未找到ID为 {script_id} 的话术或更新失败"
            
    except Exception as e:
        return f"❌ 更新话术时发生错误：{str(e)}"


@tool
def delete_script(
    script_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    删除话术
    
    Args:
        script_id: 话术ID（必填）
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="delete_script")
    
    try:
        client = get_supabase_client(ctx)
        
        response = client.table('scripts').delete().eq('id', script_id).execute()
        
        if response.data and len(response.data) > 0:
            return f"✅ 话术已删除，话术ID: {script_id}"
        else:
            return f"❌ 未找到ID为 {script_id} 的话术或删除失败"
            
    except Exception as e:
        return f"❌ 删除话术时发生错误：{str(e)}"


@tool
def recommend_script(
    product_id: Optional[int] = None,
    scenario: Optional[str] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    keywords: Optional[str] = None,
    limit: int = 5,
    runtime: ToolRuntime = None
) -> str:
    """
    智能推荐话术
    
    根据场景、行业、客户类型等条件，推荐最合适的话术。
    
    Args:
        product_id: 产品ID筛选
        scenario: 使用场景
        industry: 行业
        customer_type: 客户类型
        keywords: 关键词搜索
        limit: 返回数量限制（默认5条）
    
    Returns:
        推荐的话术列表
    """
    ctx = runtime.context if runtime else new_context(method="recommend_script")
    
    try:
        client = get_supabase_client(ctx)
        
        query = client.table('scripts').select('*')
        
        # 添加筛选条件
        if product_id:
            query = query.eq('product_id', product_id)
        if scenario:
            query = query.ilike('scenario', f'%{scenario}%')
        if industry:
            query = query.eq('industry', industry)
        if customer_type:
            query = query.eq('customer_type', customer_type)
        
        # 按评分和使用次数排序
        response = query.limit(limit * 2).order('effectiveness_score', desc=True).order('usage_count', desc=True).execute()
        
        if not response.data:
            return "未找到匹配的话术，建议添加更多话术"
        
        scripts_data = cast(List[Dict[str, Any]], response.data)
        
        # 如果有关键词，进行文本匹配排序
        if keywords:
            keyword_list = keywords.lower().split()
            scored_scripts: List[tuple] = []
            for script in scripts_data:
                score = 0
                title = str(script.get('title', '')).lower()
                content = str(script.get('content', '')).lower()
                script_keywords = script.get('keywords', [])
                
                for kw in keyword_list:
                    if kw in title:
                        score += 3
                    if kw in content:
                        score += 1
                    if script_keywords and any(kw in str(k).lower() for k in script_keywords):
                        score += 2
                
                scored_scripts.append((score, script))
            
            scored_scripts.sort(key=lambda x: x[0], reverse=True)
            scripts_data = [s[1] for s in scored_scripts[:limit]]
        else:
            scripts_data = scripts_data[:limit]
        
        if not scripts_data:
            return "未找到匹配的话术"
        
        result = f"💡 为您推荐 {len(scripts_data)} 条话术：\n\n"
        
        for idx, script in enumerate(scripts_data, 1):
            score = script.get('effectiveness_score')
            score_str = f"{float(score):.1f}" if isinstance(score, (int, float)) else "未评分"
            ai_flag = "🤖" if script.get('is_ai_generated') else "👤"
            
            result += f"━━━ 推荐 {idx} {ai_flag} ━━━\n"
            result += f"📌 标题: {script.get('title', '未知')}\n"
            result += f"📊 评分: {score_str} | 使用次数: {script.get('usage_count', 0)}\n"
            result += f"💬 内容:\n{script.get('content', '无内容')}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ 推荐话术时发生错误：{str(e)}"


@tool
def record_script_usage(
    script_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    记录话术使用次数
    
    Args:
        script_id: 话术ID（必填）
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="record_script_usage")
    
    try:
        client = get_supabase_client(ctx)
        
        # 先获取当前使用次数
        response = client.table('scripts').select('usage_count').eq('id', script_id).execute()
        
        if not response.data:
            return f"❌ 未找到ID为 {script_id} 的话术"
        
        script = cast(Dict[str, Any], response.data[0])
        current_count = int(script.get('usage_count', 0) or 0)
        new_count = current_count + 1
        
        # 更新使用次数
        update_response = client.table('scripts').update({"usage_count": new_count}).eq('id', script_id).execute()
        
        if update_response.data:
            return f"✅ 已记录使用，当前使用次数: {new_count}"
        else:
            return "❌ 记录使用次数失败"
            
    except Exception as e:
        return f"❌ 记录使用次数时发生错误：{str(e)}"


@tool
def get_script_statistics(
    product_id: Optional[int] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    获取话术统计数据
    
    Args:
        product_id: 产品ID，可选。不传则统计全部话术
    
    Returns:
        话术统计信息
    """
    ctx = runtime.context if runtime else new_context(method="get_script_statistics")
    
    try:
        client = get_supabase_client(ctx)
        
        # 构建查询
        query = client.table('scripts').select('category, effectiveness_score, usage_count, is_ai_generated')
        if product_id:
            query = query.eq('product_id', product_id)
        
        response = query.execute()
        
        if not response.data:
            return "暂无话术数据"
        
        scripts = cast(List[Dict[str, Any]], response.data)
        
        # 统计各分类话术数量
        category_counts: Dict[str, int] = {}
        total_usage = 0
        total_score = 0.0
        score_count = 0
        ai_count = 0
        
        for script in scripts:
            # 分类统计
            cat = str(script.get('category', 'unknown'))
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # 使用次数统计
            usage = int(script.get('usage_count', 0) or 0)
            total_usage += usage
            
            # 评分统计
            score = script.get('effectiveness_score')
            if isinstance(score, (int, float)):
                total_score += float(score)
                score_count += 1
            
            # AI生成统计
            if script.get('is_ai_generated'):
                ai_count += 1
        
        # 分类名称映射
        category_names: Dict[str, str] = {
            "opening": "开场白",
            "introduction": "产品介绍",
            "objection": "异议处理",
            "closing": "成交话术",
            "follow_up": "跟进话术",
            "general": "通用话术"
        }
        
        avg_score = total_score / score_count if score_count > 0 else 0
        
        result = "📊 话术统计信息\n\n"
        result += f"📋 总话术数: {len(scripts)} 条\n"
        result += f"🤖 AI生成: {ai_count} 条 | 👤 人工创建: {len(scripts) - ai_count} 条\n"
        result += f"📈 平均评分: {avg_score:.1f}\n"
        result += f"🔢 总使用次数: {total_usage} 次\n\n"
        
        result += "📋 分类分布：\n"
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            result += f"  - {category_names.get(cat, cat)}: {count} 条\n"
        
        return result
        
    except Exception as e:
        return f"❌ 获取统计数据时发生错误：{str(e)}"
