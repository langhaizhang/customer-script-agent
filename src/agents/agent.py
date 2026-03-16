"""
客户资源和话术管理 Agent
提供产品管理、客户资源管理、话术库管理、资料库管理、文档处理等智能化服务
支持多产品/业务线管理
"""

import os
import json
from typing import Annotated
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver

# 导入产品管理工具
from tools.product_management_tool import (
    create_product,
    query_products,
    get_product,
    update_product,
    delete_product
)

# 导入资料库管理工具
from tools.knowledge_base_tool import (
    add_knowledge,
    query_knowledge,
    get_knowledge,
    update_knowledge,
    delete_knowledge,
    get_knowledge_for_script,
    get_product_knowledge_summary
)

# 导入客户管理工具
from tools.customer_management_tool import (
    add_customer,
    query_customers,
    update_customer,
    delete_customer,
    classify_customer,
    get_customer_statistics
)

# 导入话术管理工具
from tools.script_management_tool import (
    add_script,
    query_scripts,
    update_script,
    delete_script,
    recommend_script,
    record_script_usage,
    get_script_statistics
)

# 导入文档处理工具
from tools.document_processing_tool import (
    parse_document,
    extract_customers_from_document,
    batch_import_customers,
    batch_import_scripts,
    export_customers_to_json
)

# 导入智能录入工具
from tools.smart_input_tool import (
    parse_text_to_customer,
    parse_image_to_customer,
    smart_add_customer
)

# 导入AI话术生成工具
from tools.ai_script_generator import (
    generate_script,
    improve_script,
    generate_script_variants
)

# 导入对话收集工具
from tools.conversation_tool import (
    save_conversation,
    query_conversations,
    get_conversation,
    analyze_customer_conversations,
    update_conversation
)

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40

def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore

class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]

def build_agent(ctx=None):
    """构建客户资源和话术管理 Agent"""
    
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    # 初始化 LLM
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )

    # 所有工具列表
    all_tools = [
        # 产品管理工具
        create_product,
        query_products,
        get_product,
        update_product,
        delete_product,
        
        # 资料库管理工具
        add_knowledge,
        query_knowledge,
        get_knowledge,
        update_knowledge,
        delete_knowledge,
        get_knowledge_for_script,
        get_product_knowledge_summary,
        
        # 客户管理工具
        add_customer,
        query_customers,
        update_customer,
        delete_customer,
        classify_customer,
        get_customer_statistics,
        
        # 话术管理工具
        add_script,
        query_scripts,
        update_script,
        delete_script,
        recommend_script,
        record_script_usage,
        get_script_statistics,
        
        # 文档处理工具
        parse_document,
        extract_customers_from_document,
        batch_import_customers,
        batch_import_scripts,
        export_customers_to_json,
        
        # 智能录入工具
        parse_text_to_customer,
        parse_image_to_customer,
        smart_add_customer,
        
        # AI话术生成工具
        generate_script,
        improve_script,
        generate_script_variants,
        
        # 对话收集工具
        save_conversation,
        query_conversations,
        get_conversation,
        analyze_customer_conversations,
        update_conversation
    ]

    # 创建 Agent
    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=all_tools,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
