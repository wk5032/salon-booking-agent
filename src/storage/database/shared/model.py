from coze_coding_dev_sdk.database import Base

from typing import Optional
import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Double, Float, ForeignKey, Index, Integer, Numeric, PrimaryKeyConstraint, String, Table, Text, text, func
from sqlalchemy.dialects.postgresql import OID
from sqlalchemy.orm import Mapped, mapped_column

class HealthCheck(Base):
    __tablename__ = 'health_check'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='health_check_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))


# ============ 发廊预约系统表结构 ============

class Service(Base):
    """服务项目表"""
    __tablename__ = "services"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="服务名称，如：剪发、烫发、染发")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, comment="服务时长（分钟）")
    price: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False, comment="服务价格")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="服务描述")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true", comment="是否可用")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    __table_args__ = (
        Index("ix_services_name", "name"),
        Index("ix_services_is_active", "is_active"),
    )


class Stylist(Base):
    """发型师表"""
    __tablename__ = "stylists"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="发型师姓名")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="联系电话")
    work_start_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="09:00", comment="工作开始时间，格式HH:MM")
    work_end_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="18:00", comment="工作结束时间，格式HH:MM")
    slot_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30", comment="时间槽间隔（分钟）")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true", comment="是否在职")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    __table_args__ = (
        Index("ix_stylists_name", "name"),
        Index("ix_stylists_is_active", "is_active"),
    )


class StylistService(Base):
    """发型师-服务项目关联表"""
    __tablename__ = "stylist_services"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stylist_id: Mapped[int] = mapped_column(Integer, ForeignKey("stylists.id"), nullable=False, comment="发型师ID")
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id"), nullable=False, comment="服务项目ID")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("ix_stylist_services_stylist_id", "stylist_id"),
        Index("ix_stylist_services_service_id", "service_id"),
    )


class Appointment(Base):
    """预约记录表"""
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="客户姓名")
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="客户电话")
    stylist_id: Mapped[int] = mapped_column(Integer, ForeignKey("stylists.id"), nullable=False, comment="发型师ID")
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id"), nullable=False, comment="服务项目ID")
    appointment_date: Mapped[str] = mapped_column(String(10), nullable=False, comment="预约日期，格式YYYY-MM-DD")
    appointment_time: Mapped[str] = mapped_column(String(5), nullable=False, comment="预约时间，格式HH:MM")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="confirmed", comment="状态：confirmed/cancelled/completed")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    __table_args__ = (
        Index("ix_appointments_stylist_id", "stylist_id"),
        Index("ix_appointments_service_id", "service_id"),
        Index("ix_appointments_date", "appointment_date"),
        Index("ix_appointments_status", "status"),
        Index("ix_appointments_customer_phone", "customer_phone"),
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
