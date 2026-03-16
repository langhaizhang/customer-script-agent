"""
文档处理工具
提供文档解析、客户信息提取、批量导入等功能
"""

from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.supabase_client import get_supabase_client
from coze_coding_dev_sdk.fetch import FetchClient
from coze_coding_dev_sdk import KnowledgeClient, Config, KnowledgeDocument, DataSourceType
from typing import Optional, List, Dict, Any
import json
import re


@tool
def parse_document(
    document_url: str,
    runtime: ToolRuntime = None
) -> str:
    """
    解析文档（支持 Excel、Word、PDF 等格式）并提取内容
    
    Args:
        document_url: 文档URL地址（必填）
    
    Returns:
        文档内容
    """
    ctx = runtime.context if runtime else new_context(method="parse_document")
    
    try:
        client = FetchClient(ctx=ctx)
        
        response = client.fetch(url=document_url)
        
        if response.status_code != 0:
            return f"❌ 文档解析失败：{response.status_message}"
        
        # 提取文本内容
        text_content = []
        for item in response.content:
            if item.type == "text" and item.text:
                text_content.append(item.text)
        
        if not text_content:
            return "❌ 文档中未找到文本内容"
        
        result = f"📄 文档解析成功\n\n"
        result += f"文档标题: {response.title or '未知'}\n"
        result += f"文档类型: {response.filetype or '未知'}\n"
        result += f"\n内容预览:\n"
        result += "-" * 60 + "\n"
        
        # 显示前1000个字符
        full_text = "\n".join(text_content)
        preview_text = full_text[:1000]
        if len(full_text) > 1000:
            preview_text += "\n\n...(内容过长，已截断)"
        
        result += preview_text
        
        return result
        
    except Exception as e:
        return f"❌ 解析文档时发生错误：{str(e)}"


@tool
def extract_customers_from_document(
    document_url: str,
    runtime: ToolRuntime = None
) -> str:
    """
    从文档中提取客户信息（智能识别姓名、电话、邮箱、公司等字段）
    
    Args:
        document_url: 文档URL地址（必填）
    
    Returns:
        提取的客户信息列表
    """
    ctx = runtime.context if runtime else new_context(method="extract_customers_from_document")
    
    try:
        client = FetchClient(ctx=ctx)
        
        response = client.fetch(url=document_url)
        
        if response.status_code != 0:
            return f"❌ 文档解析失败：{response.status_message}"
        
        # 提取文本内容
        text_content = []
        for item in response.content:
            if item.type == "text" and item.text:
                text_content.append(item.text)
        
        if not text_content:
            return "❌ 文档中未找到文本内容"
        
        full_text = "\n".join(text_content)
        
        # 使用正则表达式提取客户信息
        customers = []
        
        # 提取电话号码
        phone_pattern = r'(?:电话|手机|联系方式|手机号)[：:]\s*([1][3-9]\d{9})'
        phones = re.findall(phone_pattern, full_text)
        
        # 提取邮箱
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, full_text)
        
        # 提取姓名（简单模式：姓名/联系人后跟2-4个汉字）
        name_pattern = r'(?:姓名|联系人|客户名)[：:]\s*([\u4e00-\u9fa5]{2,4})'
        names = re.findall(name_pattern, full_text)
        
        # 提取公司名称
        company_pattern = r'(?:公司|企业|单位)[：:]\s*([^\n]+?)(?:\s|$)'
        companies = re.findall(company_pattern, full_text)
        
        # 提取行业
        industry_pattern = r'(?:行业|领域)[：:]\s*([^\n]+?)(?:\s|$)'
        industries = re.findall(industry_pattern, full_text)
        
        result = f"📋 从文档中提取的客户信息：\n\n"
        
        if names:
            result += f"姓名: {', '.join(names[:10])}\n"
        if phones:
            result += f"电话: {', '.join(phones[:10])}\n"
        if emails:
            result += f"邮箱: {', '.join(emails[:10])}\n"
        if companies:
            result += f"公司: {', '.join(companies[:10])}\n"
        if industries:
            result += f"行业: {', '.join(industries[:10])}\n"
        
        if not any([names, phones, emails, companies, industries]):
            result += "⚠️ 未识别到明显的客户信息\n\n"
            result += "提示：请确保文档包含以下格式的信息：\n"
            result += "- 姓名/联系人: XXX\n"
            result += "- 电话/手机: 138XXXX XXXX\n"
            result += "- 邮箱: xxx@xxx.com\n"
            result += "- 公司: XXX公司\n"
        
        return result
        
    except Exception as e:
        return f"❌ 提取客户信息时发生错误：{str(e)}"


@tool
def batch_import_customers(
    customers_json: str,
    runtime: ToolRuntime = None
) -> str:
    """
    批量导入客户信息到数据库
    
    Args:
        customers_json: 客户信息JSON数组字符串（必填）
            格式示例：
            [
                {
                    "name": "张三",
                    "company": "XX公司",
                    "phone": "13800138000",
                    "email": "zhangsan@example.com",
                    "industry": "互联网",
                    "customer_type": "potential",
                    "status": "active",
                    "tags": ["VIP", "重要客户"],
                    "notes": "备注信息",
                    "source": "展会"
                }
            ]
    
    Returns:
        导入结果信息
    """
    ctx = runtime.context if runtime else new_context(method="batch_import_customers")
    
    try:
        # 解析JSON
        customers_data = json.loads(customers_json)
        
        if not isinstance(customers_data, list):
            return "❌ 数据格式错误：需要提供客户信息数组"
        
        client = get_supabase_client(ctx)
        
        success_count = 0
        fail_count = 0
        errors = []
        
        for idx, customer in enumerate(customers_data, 1):
            try:
                # 验证必填字段
                if not customer.get('name'):
                    errors.append(f"第{idx}条：缺少姓名字段")
                    fail_count += 1
                    continue
                
                # 准备数据
                customer_record = {
                    "name": customer['name'],
                    "customer_type": customer.get('customer_type', 'potential'),
                    "status": customer.get('status', 'active')
                }
                
                # 添加可选字段
                optional_fields = ['company', 'phone', 'email', 'industry', 'tags', 'notes', 'source']
                for field in optional_fields:
                    if customer.get(field):
                        customer_record[field] = customer[field]
                
                # 插入数据库
                response = client.table('customers').insert(customer_record).execute()
                
                if response.data:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"第{idx}条：插入失败")
                    
            except Exception as e:
                fail_count += 1
                errors.append(f"第{idx}条：{str(e)}")
        
        # 格式化结果
        result = f"📥 批量导入完成\n\n"
        result += f"✅ 成功: {success_count} 条\n"
        result += f"❌ 失败: {fail_count} 条\n"
        
        if errors:
            result += f"\n错误详情:\n"
            for error in errors[:10]:  # 只显示前10条错误
                result += f"  - {error}\n"
            if len(errors) > 10:
                result += f"  ...(还有 {len(errors) - 10} 条错误未显示)\n"
        
        return result
        
    except json.JSONDecodeError as e:
        return f"❌ JSON解析错误：{str(e)}\n\n请确保提供有效的JSON格式数据"
    except Exception as e:
        return f"❌ 批量导入时发生错误：{str(e)}"


@tool
def batch_import_scripts(
    scripts_json: str,
    runtime: ToolRuntime = None
) -> str:
    """
    批量导入话术到话术库
    
    Args:
        scripts_json: 话术信息JSON数组字符串（必填）
            格式示例：
            [
                {
                    "title": "开场白-问候",
                    "content": "您好，我是XX公司的XX，很高兴为您服务...",
                    "category": "opening",
                    "scenario": "首次接触客户",
                    "keywords": ["问候", "开场", "首次联系"],
                    "industry": "通用",
                    "customer_type": "potential",
                    "effectiveness_score": 8.5
                }
            ]
    
    Returns:
        导入结果信息
    """
    ctx = runtime.context if runtime else new_context(method="batch_import_scripts")
    
    try:
        # 解析JSON
        scripts_data = json.loads(scripts_json)
        
        if not isinstance(scripts_data, list):
            return "❌ 数据格式错误：需要提供话术信息数组"
        
        client = get_supabase_client(ctx)
        knowledge_client = KnowledgeClient(config=Config(), ctx=ctx)
        
        success_count = 0
        fail_count = 0
        errors = []
        
        for idx, script in enumerate(scripts_data, 1):
            try:
                # 验证必填字段
                if not script.get('title') or not script.get('content'):
                    errors.append(f"第{idx}条：缺少标题或内容字段")
                    fail_count += 1
                    continue
                
                # 准备数据
                script_record = {
                    "title": script['title'],
                    "content": script['content'],
                    "category": script.get('category', 'general')
                }
                
                # 添加可选字段
                optional_fields = ['scenario', 'keywords', 'industry', 'customer_type', 'effectiveness_score']
                for field in optional_fields:
                    if script.get(field) is not None:
                        script_record[field] = script[field]
                
                # 插入数据库
                response = client.table('scripts').insert(script_record).execute()
                
                if response.data:
                    # 同步到知识库
                    try:
                        doc_content = f"标题: {script['title']}\n\n内容: {script['content']}\n\n"
                        if script.get('scenario'):
                            doc_content += f"使用场景: {script['scenario']}\n"
                        
                        doc = KnowledgeDocument(
                            source=DataSourceType.TEXT,
                            raw_data=doc_content
                        )
                        
                        knowledge_client.add_documents(
                            documents=[doc],
                            table_name="script_knowledge"
                        )
                    except:
                        pass
                    
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"第{idx}条：插入失败")
                    
            except Exception as e:
                fail_count += 1
                errors.append(f"第{idx}条：{str(e)}")
        
        # 格式化结果
        result = f"📥 批量导入完成\n\n"
        result += f"✅ 成功: {success_count} 条\n"
        result += f"❌ 失败: {fail_count} 条\n"
        
        if errors:
            result += f"\n错误详情:\n"
            for error in errors[:10]:
                result += f"  - {error}\n"
            if len(errors) > 10:
                result += f"  ...(还有 {len(errors) - 10} 条错误未显示)\n"
        
        return result
        
    except json.JSONDecodeError as e:
        return f"❌ JSON解析错误：{str(e)}\n\n请确保提供有效的JSON格式数据"
    except Exception as e:
        return f"❌ 批量导入时发生错误：{str(e)}"


@tool
def export_customers_to_json(
    customer_type: Optional[str] = None,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    limit: int = 100,
    runtime: ToolRuntime = None
) -> str:
    """
    导出客户信息为JSON格式
    
    Args:
        customer_type: 客户类型筛选
        status: 客户状态筛选
        industry: 行业筛选
        limit: 导出数量限制（默认100条）
    
    Returns:
        JSON格式的客户数据
    """
    ctx = runtime.context if runtime else new_context(method="export_customers_to_json")
    
    try:
        client = get_supabase_client(ctx)
        
        query = client.table('customers').select('*')
        
        # 添加筛选条件
        if customer_type:
            query = query.eq('customer_type', customer_type)
        if status:
            query = query.eq('status', status)
        if industry:
            query = query.eq('industry', industry)
        
        response = query.limit(limit).order('created_at', desc=True).execute()
        
        if not response.data:
            return "未找到匹配的客户数据"
        
        # 格式化输出
        result = f"📤 导出客户数据（共 {len(response.data)} 条）：\n\n"
        result += "```json\n"
        result += json.dumps(response.data, ensure_ascii=False, indent=2)
        result += "\n```\n"
        
        return result
        
    except Exception as e:
        return f"❌ 导出客户数据时发生错误：{str(e)}"
