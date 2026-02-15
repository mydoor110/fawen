"""
快速配置示例脚本
用于设置标准的审批流程: 副主任 → 主任 → 文件管理员
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def login():
    """登录获取token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        }
    )
    response.raise_for_status()
    data = response.json()
    return data["access_token"]


def create_approval_roles(token):
    """创建三个审批角色"""
    headers = {"Authorization": f"Bearer {token}"}
    
    roles = [
        {"name": "副主任", "level": 1, "description": "副主任审批层级"},
        {"name": "主任", "level": 2, "description": "主任审批层级"},
        {"name": "文件管理员", "level": 3, "description": "文件管理员审批层级"}
    ]
    
    role_ids = {}
    
    for role_data in roles:
        try:
            response = requests.post(
                f"{BASE_URL}/admin/approval-roles",
                headers=headers,
                json=role_data
            )
            response.raise_for_status()
            role = response.json()
            role_ids[role_data["name"]] = role["id"]
            print(f"✅ 创建审批角色: {role_data['name']} (ID: {role['id']})")
        except Exception as e:
            print(f"❌ 创建审批角色 {role_data['name']} 失败: {e}")
    
    return role_ids


def create_approval_flow(token, role_ids):
    """创建审批流程并添加节点"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 创建审批流程
    try:
        response = requests.post(
            f"{BASE_URL}/approval/flows",
            headers=headers,
            json={
                "name": "标准公文审批流程",
                "description": "副主任→主任→文件管理员"
            }
        )
        response.raise_for_status()
        flow = response.json()
        flow_id = flow["id"]
        print(f"✅ 创建审批流程: {flow['name']} (ID: {flow_id})")
    except Exception as e:
        print(f"❌ 创建审批流程失败: {e}")
        return None
    
    # 2. 添加三个审批节点
    nodes = [
        {"role_name": "副主任", "sequence": 1},
        {"role_name": "主任", "sequence": 2},
        {"role_name": "文件管理员", "sequence": 3}
    ]
    
    for node_data in nodes:
        role_name = node_data["role_name"]
        if role_name not in role_ids:
            print(f"⚠️  跳过节点 {role_name}（角色未创建）")
            continue
        
        try:
            response = requests.post(
                f"{BASE_URL}/approval/flows/{flow_id}/nodes",
                headers=headers,
                json={
                    "approval_role_id": role_ids[role_name],
                    "sequence": node_data["sequence"],
                    "node_type": "and",
                    "timeout_days": 7
                }
            )
            response.raise_for_status()
            node = response.json()
            print(f"✅ 添加审批节点 {node_data['sequence']}: {role_name}")
        except Exception as e:
            print(f"❌ 添加审批节点 {role_name} 失败: {e}")
    
    return flow_id


def list_users(token):
    """列出所有用户"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/admin/users", headers=headers)
        response.raise_for_status()
        users = response.json()
        print(f"\n📋 系统用户列表 (共{len(users)}人):")
        for user in users:
            print(f"  - {user['real_name']} ({user['username']}) - ID: {user['id']}")
        return users
    except Exception as e:
        print(f"❌ 获取用户列表失败: {e}")
        return []


def assign_user_to_role(token, user_id, role_id, role_name):
    """将用户分配到审批角色"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/approval-roles/{user_id}",
            headers=headers,
            params={
                "approval_role_id": role_id,
                "priority": 0
            }
        )
        response.raise_for_status()
        print(f"✅ 用户 {user_id} 已分配到角色: {role_name}")
        return True
    except Exception as e:
        print(f"❌ 分配用户到角色失败: {e}")
        return False


def main():
    print("=" * 60)
    print("      公文文件号管理系统 - 快速配置脚本")
    print("=" * 60)
    print("\n本脚本将自动配置标准审批流程:")
    print("  1. 创建三个审批角色（副主任、主任、文件管理员）")
    print("  2. 创建审批流程")
    print("  3. 添加三个串行审批节点")
    print("  4. （需手动）将用户分配到相应角色\n")
    
    # 1. 登录
    print("🔐 正在登录...")
    try:
        token = login()
        print("✅ 登录成功\n")
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return
    
    # 2. 创建审批角色
    print("📝 正在创建审批角色...")
    role_ids = create_approval_roles(token)
    print()
    
    # 3. 创建审批流程
    print("🔄 正在创建审批流程...")
    flow_id = create_approval_flow(token, role_ids)
    print()
    
    # 4. 列出用户供参考
    users = list_users(token)
    
    # 5. 提示用户分配角色
    print("\n" + "=" * 60)
    print("⚠️  接下来需要手动分配用户到审批角色")
    print("=" * 60)
    print("\n请根据上面的用户列表，手动分配用户到相应角色:")
    print("\n方式A: 使用本脚本的辅助函数（需修改代码）")
    print("  在代码中调用: assign_user_to_role(token, user_id, role_id, role_name)")
    
    print("\n方式B: 使用API直接调用")
    print("  POST /admin/approval-roles/{user_id}?approval_role_id={role_id}&priority=0")
    
    print("\n方式C: 使用前端界面")
    print("  登录系统 → 用户管理 → 编辑用户 → 分配审批角色")
    
    print("\n" + "=" * 60)
    print("配置完成！审批流程已就绪。")
    print("=" * 60)
    print(f"\n审批流程ID: {flow_id}")
    print("\n创建的审批角色:")
    for role_name, role_id in role_ids.items():
        print(f"  - {role_name}: {role_id}")
    
    print("\n下一步:")
    print("  1. 分配具体用户到三个审批角色")
    print("  2. 配置电子印章（可选）:")
    print("     POST /admin/config")
    print("     {")
    print('       "config_key": "electronic_seal",')
    print('       "config_value": {')
    print('         "enabled": true,')
    print('         "image_path": "/path/to/seal.png",')
    print('         "position": "end",')
    print('         "width_inches": 1.5')
    print("       }")
    print("     }")
    print("  3. 用户提交文档时选择此审批流程")
    print()


if __name__ == "__main__":
    main()
