"""
话术库管理工具
提供话术的增删改查、智能推荐、知识库检索等功能
"""

from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client
from coze_coding_dev_sdk import KnowledgeClient, Config, KnowledgeDocument, DataSourceType
from typing import Optional, List, Dict, Any
import json


@tool
def add_script(
    title: str,
    content: str,
    category: str = "general",
    scenario: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    industry: Optional[str] = None,
    customer_type: Optional[str] = None,
    effectiveness_score: Optional[float] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    添加新话术到话术库
    
    Args:
        title: 话术标题（必填）
        content: 话术内容（必填）
        category: 话术分类（opening/introduction/objection/closing/follow_up/general）
        scenario: 使用场景
        keywords: 关键词标签列表
        industry: 适用行业
        customer_type: 适用客户类型
        effectiveness_score: 有效性评分(0-10)
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="add_script")
    
    try:
        client = get_supabase_client(ctx)
        
        script_data = {
            "title": title,
            "content": content,
            "category": category
        }
        
        # 添加可选字段
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
        
        if response.data and isinstance(response.data, list) and len(response.data) > 0:
            script_record: Dict[str, Any] = response.data[0]
            script_id = script_record['id']
            
            # 同步到知识库以便智能检索
            try:
                knowledge_client = KnowledgeClient(config=Config(), ctx=ctx)
                
                # 构建知识库文档内容
                doc_content = f"标题: {title}\n\n内容: {content}\n\n"
                if scenario:
                    doc_content += f"使用场景: {scenario}\n"
                if keywords:
                    doc_content += f"关键词: {', '.join(keywords)}\n"
                if industry:
                    doc_content += f"适用行业: {industry}\n"
                if customer_type:
                    doc_content += f"适用客户类型: {customer_type}\n"
                
                doc = KnowledgeDocument(
                    source=DataSourceType.TEXT,
                    raw_data=doc_content
                )
                
                knowledge_client.add_documents(
                    documents=[doc],
                    table_name="script_knowledge"
                )
            except Exception as e:
                # 知识库添加失败不影响主流程
                pass
            
            return f"✅ 成功添加话术：{title}\n话术ID: {script_id}"
        else:
            return "❌ 添加话术失败：未返回数据"
            
    except Exception as e:
        return f"❌ 添加话术时发生错误：{str(e)}"


@tool
def query_scripts(
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
        
        scripts_data: List[Dict[str, Any]] = response.data
        result = f"📚 找到 {len(scripts_data)} 条话术：\n\n"
        
        for idx, script in enumerate(scripts_data, 1):
            keywords_list = script.get('keywords', [])
            keywords_str = ", ".join(keywords_list) if isinstance(keywords_list, list) else "无"
            score = script.get('effectiveness_score')
            score_str = f"{score:.1f}" if isinstance(score, (int, float)) else "未评分"
            
            content_text = script.get('content', '')
            content_preview = content_text[:100] if isinstance(content_text, str) and len(content_text) > 100 else content_text
            
            result += f"{idx}. 【{script.get('title', '未知')}】\n"
            result += f"   - 分类: {script.get('category', '未知')}\n"
            result += f"   - 内容: {content_preview}...\n"
            result += f"   - 使用场景: {script.get('scenario', '通用')}\n"
            result += f"   - 关键词: {keywords_str}\n"
            result += f"   - 适用行业: {script.get('industry', '通用')}\n"
            result += f"   - 适用客户类型: {script.get('customer_type', '通用')}\n"
            result += f"   - 有效性评分: {score_str}\n"
            result += f"   - 使用次数: {script.get('usage_count', 0)}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ 查询话术时发生错误：{str(e)}"


@tool
def update_script(
    script_id: int,
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
        
        update_data = {}
        
        # 只更新提供的字段
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
        
        if response.data:
            return f"✅ 成功更新话术信息（ID: {script_id}）"
        else:
            return f"❌ 未找到ID为 {script_id} 的话术"
            
    except Exception as e:
        return f"❌ 更新话术时发生错误：{str(e)}"


@tool
def delete_script(
    script_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    删除话术信息
    
    Args:
        script_id: 话术ID（必填）
    
    Returns:
        操作结果信息
    """
    ctx = runtime.context if runtime else new_context(method="delete_script")
    
    try:
        client = get_supabase_client(ctx)
        
        response = client.table('scripts').delete().eq('id', script_id).execute()
        
        if response.data:
            return f"✅ 成功删除话术（ID: {script_id}）"
        else:
            return f"❌ 未找到ID为 {script_id} 的话术"
            
    except Exception as e:
        return f"❌ 删除话术时发生错误：{str(e)}"


@tool
def recommend_script(
    scenario: str,
    customer_type: Optional[str] = None,
    industry: Optional[str] = None,
    top_k: int = 5,
    runtime: ToolRuntime = None
) -> str:
    """
    智能推荐话术（基于知识库语义搜索）
    
    Args:
        scenario: 使用场景描述（必填）
        customer_type: 客户类型
        industry: 行业
        top_k: 返回推荐数量（默认5条）
    
    Returns:
        推荐的话术列表
    """
    ctx = runtime.context if runtime else new_context(method="recommend_script")
    
    try:
        # 构建搜索查询
        query_text = scenario
        if customer_type:
            query_text += f" {customer_type}"
        if industry:
            query_text += f" {industry}"
        
        # 使用知识库进行语义搜索
        knowledge_client = KnowledgeClient(config=Config(), ctx=ctx)
        
        response = knowledge_client.search(
            query=query_text,
            table_names=["script_knowledge"],
            top_k=top_k,
            min_score=0.5
        )
        
        if response.code != 0 or not response.chunks:
            # 如果知识库搜索失败，从数据库查询
            return query_scripts(
                category=None,
                industry=industry,
                customer_type=customer_type,
                limit=top_k,
                runtime=runtime
            )
        
        result = f"💡 为您推荐 {len(response.chunks)} 条话术：\n\n"
        
        for idx, chunk in enumerate(response.chunks, 1):
            score = chunk.score
            content = chunk.content
            
            result += f"{idx}. 【相关度: {score:.2f}】\n"
            result += f"{content}\n"
            result += "-" * 60 + "\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ 推荐话术时发生错误：{str(e)}"


@tool
def record_script_usage(
    script_id: int,
    runtime: ToolRuntime = None
) -> str:
    """
    记录话术使用次数（用于统计话术有效性）
    
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
        
        if not response.data or not isinstance(response.data, list) or len(response.data) == 0:
            return f"❌ 未找到ID为 {script_id} 的话术"
        
        script_record: Dict[str, Any] = response.data[0]
        current_count = script_record.get('usage_count', 0)
        if not isinstance(current_count, int):
            current_count = 0
        new_count = current_count + 1
        
        # 更新使用次数
        update_response = client.table('scripts').update({"usage_count": new_count}).eq('id', script_id).execute()
        
        if update_response.data:
            return f"✅ 已记录话术使用（ID: {script_id}，累计使用 {new_count} 次）"
        else:
            return f"❌ 记录使用次数失败"
            
    except Exception as e:
        return f"❌ 记录使用次数时发生错误：{str(e)}"


@tool
def get_script_statistics(
    runtime: ToolRuntime = None
) -> str:
    """
    获取话术库统计数据
    
    Returns:
        话术统计信息
    """
    ctx = runtime.context if runtime else new_context(method="get_script_statistics")
    
    try:
        client = get_supabase_client(ctx)
        
        # 获取所有话术
        response = client.table('scripts').select('category, industry, customer_type, effectiveness_score, usage_count').execute()
        
        if not response.data:
            return "暂无话术数据"
        
        scripts: List[Dict[str, Any]] = response.data
        total = len(scripts)
        
        # 统计各类话术数量
        category_stats: Dict[str, int] = {}
        industry_stats: Dict[str, int] = {}
        customer_type_stats: Dict[str, int] = {}
        total_usage = 0
        score_count = 0
        total_score = 0.0
        
        for script in scripts:
            # 分类统计
            category = script.get('category', 'unknown')
            if isinstance(category, str):
                category_stats[category] = category_stats.get(category, 0) + 1
            
            # 行业统计
            industry = script.get('industry', '通用')
            if isinstance(industry, str):
                industry_stats[industry] = industry_stats.get(industry, 0) + 1
            
            # 客户类型统计
            ctype = script.get('customer_type', '通用')
            if isinstance(ctype, str):
                customer_type_stats[ctype] = customer_type_stats.get(ctype, 0) + 1
            
            # 使用次数
            usage_count = script.get('usage_count', 0)
            if isinstance(usage_count, int):
                total_usage += usage_count
            
            # 评分统计
            score = script.get('effectiveness_score')
            if isinstance(score, (int, float)):
                score_count += 1
                total_score += score
        
        # 格式化输出
        result = f"📊 话术库统计报告\n\n"
        result += f"话术总数: {total}\n"
        result += f"累计使用次数: {total_usage}\n"
        if score_count > 0:
            avg_score = total_score / score_count
            result += f"平均有效性评分: {avg_score:.2f}\n"
        
        result += "\n话术分类分布:\n"
        category_names = {
            "opening": "开场白",
            "introduction": "产品介绍",
            "objection": "异议处理",
            "closing": "成交话术",
            "follow_up": "跟进话术",
            "general": "通用话术"
        }
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  - {category_names.get(category, category)}: {count} ({percentage:.1f}%)\n"
        
        result += "\n适用行业分布（Top 10）:\n"
        sorted_industries = sorted(industry_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        for industry, count in sorted_industries:
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  - {industry}: {count} ({percentage:.1f}%)\n"
        
        result += "\n适用客户类型分布:\n"
        for ctype, count in sorted(customer_type_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  - {ctype}: {count} ({percentage:.1f}%)\n"
        
        return result
        
    except Exception as e:
        return f"❌ 获取统计数据时发生错误：{str(e)}"
