"""API 端到端测试"""
import requests

BASE = 'http://localhost:5000/api'

# 1. 登录
r = requests.post(f'{BASE}/auth/login', data={'username': 'admin', 'password': 'admin123'})
print(f'1. 登录: {r.status_code}')
assert r.ok, f"登录失败: {r.text}"
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# 2. 创建文档
r = requests.post(f'{BASE}/documents', json={'title': '测试公文', 'document_type': '通知'}, headers=h)
print(f'2. 创建文档: {r.status_code}')
assert r.ok, f"创建文档失败: {r.text}"
doc_id = r.json()['id']

# 3. 获取文档
r = requests.get(f'{BASE}/documents/{doc_id}', headers=h)
print(f'3. 获取文档: {r.status_code} - {r.json().get("title", "")}')
assert r.ok

# 4. 更新文档
r = requests.put(f'{BASE}/documents/{doc_id}', json={'title': '测试公文-修改'}, headers=h)
print(f'4. 更新文档: {r.status_code}')
assert r.ok

# 5. 列出文档
r = requests.get(f'{BASE}/documents', headers=h)
print(f'5. 列出文档: {r.status_code} 共 {len(r.json())} 条')
assert r.ok

# 6. 列出用户
r = requests.get(f'{BASE}/admin/users', headers=h)
print(f'6. 列出用户: {r.status_code} 共 {len(r.json())} 条')
assert r.ok

# 7. 注册普通用户
r = requests.post(f'{BASE}/auth/register', json={
    'username': 'testuser2', 'password': 'Test_12345',
    'real_name': '测试', 'department': '测试部'
})
print(f'7. 注册普通用户: {r.status_code}')

# 8. 普通用户登录
r = requests.post(f'{BASE}/auth/login', data={'username': 'testuser2', 'password': 'Test_12345'})
if r.ok:
    user_token = r.json()['access_token']
    user_h = {'Authorization': f'Bearer {user_token}'}

    # 9. 普通用户列所有用户(应该403)
    r = requests.get(f'{BASE}/admin/users', headers=user_h)
    print(f'8. 普通用户列用户: {r.status_code} (期望403)')
    assert r.status_code == 403, f"应为403，实际: {r.status_code}"

    # 10. 普通用户创建文档(应该200)
    r = requests.post(f'{BASE}/documents', json={'title': '用户文档', 'document_type': '报告'}, headers=user_h)
    print(f'9. 普通用户创建文档: {r.status_code} (期望200/201)')
    assert r.ok

# 11. 审批流程
r = requests.get(f'{BASE}/approval/flows', headers=h)
print(f'10. 审批流程: {r.status_code}')
assert r.ok

# 12. 编号池
r = requests.get(f'{BASE}/numbers/pools', headers=h)
print(f'11. 编号池: {r.status_code}')
assert r.ok

# 13. 校对任务
r = requests.get(f'{BASE}/proofreading/tasks', headers=h)
print(f'12. 校对任务: {r.status_code}')
assert r.ok

# 14. 审批任务
r = requests.get(f'{BASE}/approval/tasks', headers=h)
print(f'13. 审批任务: {r.status_code}')
assert r.ok

print()
print('✅ 全部 API 测试通过!')
