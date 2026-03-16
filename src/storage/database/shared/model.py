from coze_coding_dev_sdk.database import Base

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Double, Integer, Numeric, PrimaryKeyConstraint, Table, Text, text, String, JSON, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import OID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import datetime

class HealthCheck(Base):
    __tablename__ = 'health_check'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='health_check_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))


class Customer(Base):
    """客户资源表"""
    __tablename__ = 'customers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="客户姓名")
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="公司名称")
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="联系电话")
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="邮箱")
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="所属行业")
    customer_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        server_default="potential", 
        comment="客户类型：potential(潜在客户), interested(意向客户), converted(成交客户), churned(流失客户)"
    )
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        server_default="active", 
        comment="客户状态：active(活跃), inactive(不活跃), churned(流失)"
    )
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment="客户标签")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注信息")
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="客户来源")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), 
        onupdate=func.now(), 
        nullable=True,
        comment="更新时间"
    )

    __table_args__ = (
        Index("ix_customers_name", "name"),
        Index("ix_customers_company", "company"),
        Index("ix_customers_customer_type", "customer_type"),
    )


class Script(Base):
    """话术库表"""
    __tablename__ = 'scripts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="话术标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="话术内容")
    category: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        server_default="general",
        comment="话术分类：opening(开场白), introduction(产品介绍), objection(异议处理), closing(成交话术), follow_up(跟进话术), general(通用话术)"
    )
    scenario: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="使用场景")
    keywords: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment="关键词标签")
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="适用行业")
    customer_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="适用客户类型")
    effectiveness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="有效性评分(0-10)")
    usage_count: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        server_default="0",
        comment="使用次数"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), 
        onupdate=func.now(), 
        nullable=True,
        comment="更新时间"
    )

    __table_args__ = (
        Index("ix_scripts_title", "title"),
        Index("ix_scripts_category", "category"),
        Index("ix_scripts_industry", "industry"),
    )


t_pg_stat_statements = Table(
    'pg_stat_statements', Base.metadata,
    Column('userid', OID),
    Column('dbid', OID),
    Column('toplevel', Boolean),
    Column('queryid', BigInteger),
    Column('query', Text),
    Column('plans', BigInteger),
    Column('total_plan_time', Double(53)),
    Column('min_plan_time', Double(53)),
    Column('max_plan_time', Double(53)),
    Column('mean_plan_time', Double(53)),
    Column('stddev_plan_time', Double(53)),
    Column('calls', BigInteger),
    Column('total_exec_time', Double(53)),
    Column('min_exec_time', Double(53)),
    Column('max_exec_time', Double(53)),
    Column('mean_exec_time', Double(53)),
    Column('stddev_exec_time', Double(53)),
    Column('rows', BigInteger),
    Column('shared_blks_hit', BigInteger),
    Column('shared_blks_read', BigInteger),
    Column('shared_blks_dirtied', BigInteger),
    Column('shared_blks_written', BigInteger),
    Column('local_blks_hit', BigInteger),
    Column('local_blks_read', BigInteger),
    Column('local_blks_dirtied', BigInteger),
    Column('local_blks_written', BigInteger),
    Column('temp_blks_read', BigInteger),
    Column('temp_blks_written', BigInteger),
    Column('shared_blk_read_time', Double(53)),
    Column('shared_blk_write_time', Double(53)),
    Column('local_blk_read_time', Double(53)),
    Column('local_blk_write_time', Double(53)),
    Column('temp_blk_read_time', Double(53)),
    Column('temp_blk_write_time', Double(53)),
    Column('wal_records', BigInteger),
    Column('wal_fpi', BigInteger),
    Column('wal_bytes', Numeric),
    Column('jit_functions', BigInteger),
    Column('jit_generation_time', Double(53)),
    Column('jit_inlining_count', BigInteger),
    Column('jit_inlining_time', Double(53)),
    Column('jit_optimization_count', BigInteger),
    Column('jit_optimization_time', Double(53)),
    Column('jit_emission_count', BigInteger),
    Column('jit_emission_time', Double(53)),
    Column('jit_deform_count', BigInteger),
    Column('jit_deform_time', Double(53)),
    Column('stats_since', DateTime(True)),
    Column('minmax_stats_since', DateTime(True))
)


t_pg_stat_statements_info = Table(
    'pg_stat_statements_info', Base.metadata,
    Column('dealloc', BigInteger),
    Column('stats_reset', DateTime(True))
)
