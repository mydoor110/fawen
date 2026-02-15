"""
AntFlow数据解析器
将AntFlow可视化设计器的JSON数据解析为后端的审批流程数据结构
"""
import json
import uuid
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.approval import ApprovalFlow, ApprovalNode, NodeApprovalType
from app.models.user import ApprovalRole
from app.utils.logger import get_logger

logger = get_logger("antflow_parser")


class AntFlowParser:
    """AntFlow数据解析器"""
    
    @staticmethod
    def parse_and_create_flow(db: Session, flow_data: dict, creator_id: uuid.UUID) -> Tuple[ApprovalFlow, str]:
        """
        解析AntFlow数据并创建审批流程
        
        flow_data 格式示例:
        {
          "bpmnName": "标准公文审批流程",
          "description": "副主任→主任→文件管理员",
          "nodeConfig": {
            "nodeType": "ROOT",
            "childNode": {
              "nodeType": "APPROVAL",
              "nodeName": "副主任审批",
              "nodeUserList": [{"type": 3, "targetId": "role_id", "name": "副主任"}],
              "selectMode": "AND",
              "childNode": { ... }
            }
          }
        }
        
        Returns:
            (ApprovalFlow对象, 错误消息或None)
        """
        try:
            # 1. 验证必要字段
            if not flow_data.get("bpmnName"):
                return None, "流程名称不能为空"
            
            node_config = flow_data.get("nodeConfig")
            if not node_config:
                return None, "流程配置不能为空"
            
            # 2. 创建审批流程
            flow = ApprovalFlow(
                name=flow_data.get("bpmnName", "未命名流程"),
                description=flow_data.get("description", ""),
                flow_data=json.dumps(flow_data, ensure_ascii=False),  # 保存原始数据
                is_active=True
            )
            db.add(flow)
            db.flush()  # 获取flow_id
            
            # 3. 递归解析节点并创建ApprovalNode
            node_count, error_msg = AntFlowParser._parse_node_recursive(
                db, flow.id, node_config, sequence=1
            )
            
            if error_msg:
                db.rollback()
                return None, error_msg
            
            if node_count == 0:
                db.rollback()
                return None, "流程中至少需要一个有效的审批节点"
            
            db.commit()
            logger.info(f"成功创建审批流程: {flow.name}，包含 {node_count} 个审批节点")
            return flow, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"解析AntFlow数据失败: {str(e)}", exc_info=True)
            return None, f"解析失败: {str(e)}"
    
    @staticmethod
    def _parse_node_recursive(
        db: Session, 
        flow_id: uuid.UUID, 
        node_data: dict, 
        sequence: int
    ) -> Tuple[int, Optional[str]]:
        """
        递归解析节点树
        
        Returns:
            (创建的节点数量, 错误消息或None)
        """
        child_node = node_data.get("childNode")
        
        if not child_node:
            return 0, None
        
        node_type = child_node.get("nodeType")
        node_count = 0
        
        # 仅处理审批节点（APPROVAL）
        if node_type == "APPROVAL":
            # 获取审批人配置
            node_user_list = child_node.get("nodeUserList", [])
            
            if not node_user_list:
                # 没有审批人的节点跳过，但继续解析子节点
                logger.warning(f"序号 {sequence} 的审批节点未配置审批人，已跳过")
            else:
                # 提取角色ID（type=3表示角色，type=1表示用户）
                role_configs = [
                    user for user in node_user_list 
                    if user.get("type") == 3  # 3=角色
                ]
                
                if not role_configs:
                    logger.warning(f"序号 {sequence} 的审批节点未配置审批角色，已跳过")
                else:
                    # 取第一个角色（如果有多个角色，可以创建多个节点或合并）
                    role_config = role_configs[0]
                    
                    try:
                        approval_role_id = uuid.UUID(role_config["targetId"])
                    except (ValueError, KeyError):
                        return 0, f"节点 {sequence} 的审批角色ID格式错误: {role_config.get('targetId')}"
                    
                    # 验证角色是否存在
                    role = db.query(ApprovalRole).filter(
                        ApprovalRole.id == approval_role_id
                    ).first()
                    
                    if not role:
                        return 0, f"节点 {sequence} 的审批角色不存在: {approval_role_id}"
                    
                    # 判断节点类型（AND/OR）
                    select_mode = child_node.get("selectMode", "AND")
                    node_type_enum = NodeApprovalType.AND if select_mode == "AND" else NodeApprovalType.OR
                    
                    # 获取超时天数（如果有）
                    timeout_days = child_node.get("timeoutDays", 7)
                    
                    # 创建审批节点
                    node = ApprovalNode(
                        flow_id=flow_id,
                        approval_role_id=approval_role_id,
                        sequence=sequence,
                        node_type=node_type_enum,
                        timeout_days=timeout_days
                    )
                    db.add(node)
                    node_count += 1
                    
                    logger.info(f"创建审批节点 {sequence}: {role.name} ({select_mode}模式)")
                    sequence += 1
        
        # 递归处理子节点
        if child_node.get("childNode"):
            sub_count, error_msg = AntFlowParser._parse_node_recursive(
                db, flow_id, child_node, sequence
            )
            if error_msg:
                return 0, error_msg
            node_count += sub_count
        
        return node_count, None
    
    @staticmethod
    def update_flow_from_antflow(
        db: Session, 
        flow_id: uuid.UUID, 
        flow_data: dict
    ) -> Tuple[bool, str]:
        """
        更新现有审批流程
        
        注意：这会删除原有的所有节点并重新创建
        
        Returns:
            (是否成功, 错误消息或成功消息)
        """
        try:
            # 1. 查找流程
            flow = db.query(ApprovalFlow).filter(
                ApprovalFlow.id == flow_id
            ).first()
            
            if not flow:
                return False, "审批流程不存在"
            
            # 2. 删除原有的所有节点
            deleted_count = db.query(ApprovalNode).filter(
                ApprovalNode.flow_id == flow_id
            ).delete()
            
            logger.info(f"删除流程 {flow.name} 的 {deleted_count} 个旧节点")
            
            # 3. 更新流程基本信息
            flow.name = flow_data.get("bpmnName", flow.name)
            flow.description = flow_data.get("description", flow.description)
            flow.flow_data = json.dumps(flow_data, ensure_ascii=False)
            
            # 4. 重新创建节点
            node_config = flow_data.get("nodeConfig")
            if not node_config:
                db.rollback()
                return False, "流程配置不能为空"
            
            node_count, error_msg = AntFlowParser._parse_node_recursive(
                db, flow.id, node_config, sequence=1
            )
            
            if error_msg:
                db.rollback()
                return False, error_msg
            
            if node_count == 0:
                db.rollback()
                return False, "流程中至少需要一个有效的审批节点"
            
            db.commit()
            logger.info(f"成功更新审批流程: {flow.name}，包含 {node_count} 个审批节点")
            return True, f"流程更新成功，包含 {node_count} 个审批节点"
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新审批流程失败: {str(e)}", exc_info=True)
            return False, f"更新失败: {str(e)}"
