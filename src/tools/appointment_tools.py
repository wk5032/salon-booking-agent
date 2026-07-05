"""发廊预约管理工具模块"""
from langchain.tools import tool
from postgrest.exceptions import APIError
from storage.database.supabase_client import get_supabase_client
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


def _get_client():
    """获取Supabase客户端"""
    ctx = request_context.get() or new_context(method="appointment_tool")
    return get_supabase_client()


@tool
def list_services() -> str:
    """查询所有可用的服务项目列表。
    
    返回格式：JSON数组，包含服务ID、名称、时长(分钟)、价格等信息。
    
    使用场景：当客户询问"有什么服务"、"能做什么项目"、"价格多少"时调用。
    """
    client = _get_client()
    try:
        response = client.table('services').select('id, name, duration_minutes, price, description').eq('is_active', True).order('id').execute()
        services: List[Dict[str, Any]] = response.data if response.data else []
        if not services:
            return json.dumps({"success": True, "data": [], "message": "暂无可用服务项目"}, ensure_ascii=False)
        return json.dumps({"success": True, "data": services}, ensure_ascii=False)
    except APIError as e:
        logger.error(f"查询服务项目失败: {e.message}")
        return json.dumps({"success": False, "error": f"查询失败: {e.message}"}, ensure_ascii=False)


@tool
def list_stylists() -> str:
    """查询所有在职的发型师列表。
    
    返回格式：JSON数组，包含发型师ID、姓名、工作时间等信息。
    
    使用场景：当客户询问"有哪些发型师"、"谁可以服务"时调用。
    """
    client = _get_client()
    try:
        response = client.table('stylists').select('id, name, phone, work_start_time, work_end_time').eq('is_active', True).order('id').execute()
        stylists: List[Dict[str, Any]] = response.data if response.data else []
        if not stylists:
            return json.dumps({"success": True, "data": [], "message": "暂无在职发型师"}, ensure_ascii=False)
        return json.dumps({"success": True, "data": stylists}, ensure_ascii=False)
    except APIError as e:
        logger.error(f"查询发型师列表失败: {e.message}")
        return json.dumps({"success": False, "error": f"查询失败: {e.message}"}, ensure_ascii=False)


@tool
def get_available_slots(stylist_id: int, date: str) -> str:
    """查询指定发型师在指定日期的可用时间段。
    
    参数：
    - stylist_id: 发型师ID（整数）
    - date: 日期，格式为 YYYY-MM-DD
    
    返回格式：JSON对象，包含可用时间段列表。
    
    使用场景：当客户询问"某天有什么时间"、"某个发型师什么时候有空"时调用。
    """
    client = _get_client()
    try:
        # 1. 获取发型师信息
        stylist_resp = client.table('stylists').select('id, work_start_time, work_end_time, slot_interval_minutes').eq('id', stylist_id).maybe_single().execute()
        if stylist_resp is None or not stylist_resp.data:
            return json.dumps({"success": False, "error": "发型师不存在"}, ensure_ascii=False)
        
        stylist: Dict[str, Any] = stylist_resp.data
        work_start: str = str(stylist.get('work_start_time', '09:00'))
        work_end: str = str(stylist.get('work_end_time', '18:00'))
        interval: int = int(stylist.get('slot_interval_minutes', 30))
        
        # 2. 查询该日期已有的预约
        appointments_resp = client.table('appointments').select('appointment_time, service_id').eq('stylist_id', stylist_id).eq('appointment_date', date).eq('status', 'confirmed').execute()
        appointments: List[Dict[str, Any]] = appointments_resp.data if appointments_resp.data else []
        booked_times: set = set()
        
        # 获取每个预约的服务时长，计算占用的时间段
        if appointments:
            service_ids: List[int] = list(set([int(apt.get('service_id', 0)) for apt in appointments]))
            services_resp = client.table('services').select('id, duration_minutes').in_('id', service_ids).execute()
            services_data: List[Dict[str, Any]] = services_resp.data if services_resp.data else []
            service_duration_map: Dict[int, int] = {int(s.get('id', 0)): int(s.get('duration_minutes', 30)) for s in services_data}
            
            for apt in appointments:
                booked_time: str = str(apt.get('appointment_time', ''))
                service_id_val: int = int(apt.get('service_id', 0))
                duration: int = service_duration_map.get(service_id_val, 30)
                # 计算该预约占用的所有时间段
                time_parts: List[str] = booked_time.split(':')
                if len(time_parts) != 2:
                    continue
                start_hour: int = int(time_parts[0])
                start_min: int = int(time_parts[1])
                slots_needed: int = (duration + interval - 1) // interval  # 向上取整
                for i in range(slots_needed):
                    total_min: int = start_hour * 60 + start_min + i * interval
                    h: int
                    m: int
                    h, m = divmod(total_min, 60)
                    booked_times.add(f"{h:02d}:{m:02d}")
        
        # 3. 生成所有可用时间段
        all_slots: List[str] = []
        start_parts: List[str] = work_start.split(':')
        end_parts: List[str] = work_end.split(':')
        start_hour_val: int = int(start_parts[0])
        start_min_val: int = int(start_parts[1])
        end_hour_val: int = int(end_parts[0])
        end_min_val: int = int(end_parts[1])
        
        current_min: int = start_hour_val * 60 + start_min_val
        end_total_min: int = end_hour_val * 60 + end_min_val
        
        while current_min < end_total_min:
            h_val: int
            m_val: int
            h_val, m_val = divmod(current_min, 60)
            time_str: str = f"{h_val:02d}:{m_val:02d}"
            if time_str not in booked_times:
                all_slots.append(time_str)
            current_min += interval
        
        return json.dumps({
            "success": True,
            "data": {
                "stylist_id": stylist_id,
                "date": date,
                "available_slots": all_slots,
                "booked_count": len(booked_times),
                "total_slots": len(all_slots) + len(booked_times)
            }
        }, ensure_ascii=False)
    except APIError as e:
        logger.error(f"查询可用时间段失败: {e.message}")
        return json.dumps({"success": False, "error": f"查询失败: {e.message}"}, ensure_ascii=False)


@tool
def create_appointment(customer_name: str, customer_phone: str, stylist_id: int, service_id: int, appointment_date: str, appointment_time: str, notes: str = "") -> str:
    """创建新的预约记录。
    
    参数：
    - customer_name: 客户姓名（必填）
    - customer_phone: 客户电话（必填）
    - stylist_id: 发型师ID（必填，整数）
    - service_id: 服务项目ID（必填，整数）
    - appointment_date: 预约日期，格式 YYYY-MM-DD（必填）
    - appointment_time: 预约时间，格式 HH:MM（必填）
    - notes: 备注信息（可选）
    
    返回格式：JSON对象，包含预约ID和预约详情。
    
    使用场景：当客户确认预约信息后调用，创建预约记录。
    """
    client = _get_client()
    try:
        # 验证时间段是否可用
        slots_resp = client.table('appointments').select('id').eq('stylist_id', stylist_id).eq('appointment_date', appointment_date).eq('appointment_time', appointment_time).eq('status', 'confirmed').execute()
        existing: List[Dict[str, Any]] = slots_resp.data if slots_resp.data else []
        if existing:
            return json.dumps({"success": False, "error": "该时间段已被预约，请选择其他时间"}, ensure_ascii=False)
        
        # 创建预约
        appointment_data: Dict[str, Any] = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "stylist_id": stylist_id,
            "service_id": service_id,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "status": "confirmed",
            "notes": notes
        }
        
        response = client.table('appointments').insert(appointment_data).execute()
        new_data: List[Dict[str, Any]] = response.data if response.data else []
        if not new_data:
            return json.dumps({"success": False, "error": "创建预约失败"}, ensure_ascii=False)
        new_appointment: Dict[str, Any] = new_data[0]
        
        # 获取关联的服务和发型师信息
        service_resp = client.table('services').select('name, price, duration_minutes').eq('id', service_id).maybe_single().execute()
        stylist_resp = client.table('stylists').select('name').eq('id', stylist_id).maybe_single().execute()
        
        service_info: Dict[str, Any] = service_resp.data if service_resp and service_resp.data else {}
        stylist_info: Dict[str, Any] = stylist_resp.data if stylist_resp and stylist_resp.data else {}
        
        result: Dict[str, Any] = {
            "appointment_id": new_appointment.get('id'),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "stylist_name": stylist_info.get('name', "未知"),
            "service_name": service_info.get('name', "未知"),
            "price": service_info.get('price', 0),
            "duration_minutes": service_info.get('duration_minutes', 0),
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "status": "confirmed"
        }
        
        return json.dumps({"success": True, "data": result, "message": "预约创建成功"}, ensure_ascii=False)
    except APIError as e:
        logger.error(f"创建预约失败: {e.message}")
        return json.dumps({"success": False, "error": f"创建失败: {e.message}"}, ensure_ascii=False)


@tool
def query_appointments(customer_phone: str = "", appointment_date: str = "") -> str:
    """查询预约记录。
    
    参数：
    - customer_phone: 客户电话（可选，用于查询特定客户的预约）
    - appointment_date: 预约日期（可选，格式 YYYY-MM-DD，用于查询特定日期的预约）
    
    返回格式：JSON数组，包含预约详情列表。
    
    使用场景：当客户询问"我的预约"、"查一下预约"、"某天有哪些预约"时调用。
    """
    client = _get_client()
    try:
        query = client.table('appointments').select('id, customer_name, customer_phone, stylist_id, service_id, appointment_date, appointment_time, status, notes').neq('status', 'cancelled')
        
        if customer_phone:
            query = query.eq('customer_phone', customer_phone)
        if appointment_date:
            query = query.eq('appointment_date', appointment_date)
        
        query = query.order('appointment_date').order('appointment_time')
        response = query.execute()
        appointments: List[Dict[str, Any]] = response.data if response.data else []
        
        if not appointments:
            return json.dumps({"success": True, "data": [], "message": "未找到相关预约记录"}, ensure_ascii=False)
        
        # 获取关联的服务和发型师信息
        stylist_ids: List[int] = list(set([int(apt.get('stylist_id', 0)) for apt in appointments]))
        service_ids: List[int] = list(set([int(apt.get('service_id', 0)) for apt in appointments]))
        
        stylists_resp = client.table('stylists').select('id, name').in_('id', stylist_ids).execute()
        services_resp = client.table('services').select('id, name, price, duration_minutes').in_('id', service_ids).execute()
        
        stylists_data: List[Dict[str, Any]] = stylists_resp.data if stylists_resp.data else []
        services_data: List[Dict[str, Any]] = services_resp.data if services_resp.data else []
        
        stylist_map: Dict[int, str] = {int(s.get('id', 0)): str(s.get('name', '未知')) for s in stylists_data}
        service_map: Dict[int, Dict[str, Any]] = {int(s.get('id', 0)): s for s in services_data}
        
        # 组装结果
        results: List[Dict[str, Any]] = []
        for apt in appointments:
            service_info: Dict[str, Any] = service_map.get(int(apt.get('service_id', 0)), {})
            results.append({
                "appointment_id": apt.get('id'),
                "customer_name": apt.get('customer_name', ''),
                "customer_phone": apt.get('customer_phone', ''),
                "stylist_name": stylist_map.get(int(apt.get('stylist_id', 0)), "未知"),
                "service_name": service_info.get('name', '未知'),
                "price": service_info.get('price', 0),
                "duration_minutes": service_info.get('duration_minutes', 0),
                "appointment_date": apt.get('appointment_date', ''),
                "appointment_time": apt.get('appointment_time', ''),
                "status": apt.get('status', ''),
                "notes": apt.get('notes') or ""
            })
        
        return json.dumps({"success": True, "data": results}, ensure_ascii=False)
    except APIError as e:
        logger.error(f"查询预约失败: {e.message}")
        return json.dumps({"success": False, "error": f"查询失败: {e.message}"}, ensure_ascii=False)


@tool
def cancel_appointment(appointment_id: int) -> str:
    """取消预约。
    
    参数：
    - appointment_id: 预约ID（整数）
    
    返回格式：JSON对象，包含操作结果。
    
    使用场景：当客户要求取消预约时调用。
    """
    client = _get_client()
    try:
        # 先查询预约是否存在
        apt_resp = client.table('appointments').select('id, status').eq('id', appointment_id).maybe_single().execute()
        if apt_resp is None or not apt_resp.data:
            return json.dumps({"success": False, "error": "预约记录不存在"}, ensure_ascii=False)
        
        apt_data: Dict[str, Any] = apt_resp.data
        if apt_data.get('status') == 'cancelled':
            return json.dumps({"success": False, "error": "该预约已经被取消"}, ensure_ascii=False)
        
        # 更新状态为已取消
        response = client.table('appointments').update({'status': 'cancelled'}).eq('id', appointment_id).execute()
        
        if response.data:
            return json.dumps({"success": True, "message": "预约已成功取消"}, ensure_ascii=False)
        else:
            return json.dumps({"success": False, "error": "取消失败，请重试"}, ensure_ascii=False)
    except APIError as e:
        logger.error(f"取消预约失败: {e.message}")
        return json.dumps({"success": False, "error": f"取消失败: {e.message}"}, ensure_ascii=False)


@tool
def get_stylist_services(stylist_id: int) -> str:
    """查询指定发型师可提供的服务项目。
    
    参数：
    - stylist_id: 发型师ID（整数）
    
    返回格式：JSON数组，包含该发型师可提供的服务列表。
    
    使用场景：当客户询问"某个发型师能做什么项目"时调用。
    """
    client = _get_client()
    try:
        # 查询发型师-服务关联
        resp = client.table('stylist_services').select('service_id').eq('stylist_id', stylist_id).execute()
        relations: List[Dict[str, Any]] = resp.data if resp.data else []
        
        if not relations:
            # 如果没有关联，返回所有服务（假设所有发型师都能做所有服务）
            services_resp = client.table('services').select('id, name, duration_minutes, price, description').eq('is_active', True).execute()
            services_data: List[Dict[str, Any]] = services_resp.data if services_resp.data else []
            return json.dumps({"success": True, "data": services_data, "message": "该发型师可提供所有服务"}, ensure_ascii=False)
        
        service_ids: List[int] = [int(r.get('service_id', 0)) for r in relations]
        services_resp = client.table('services').select('id, name, duration_minutes, price, description').in_('id', service_ids).eq('is_active', True).execute()
        services_data = services_resp.data if services_resp.data else []
        
        return json.dumps({"success": True, "data": services_data}, ensure_ascii=False)
    except APIError as e:
        logger.error(f"查询发型师服务失败: {e.message}")
        return json.dumps({"success": False, "error": f"查询失败: {e.message}"}, ensure_ascii=False)
