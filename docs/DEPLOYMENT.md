# 部署指南

## 环境要求

- Python 3.11+
- PostgreSQL 15+
- 推荐使用 Linux 或 macOS

## 快速启动

### 1. 克隆项目
```bash
git clone <repository-url>
cd fawen
```

### 2. 运行启动脚本

**Linux / macOS:**
```bash
./start.sh
```

**Windows:**
```cmd
start.bat
```

### 3. 激活虚拟环境并启动服务

**Linux / macOS:**
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

**Windows:**
```cmd
venv\Scripts\activate.bat
uvicorn app.main:app --reload
```

服务启动后，访问 http://localhost:8000/docs 查看 API 文档。

## 详细配置

### 数据库配置

编辑 `config.yaml` 文件，修改数据库连接信息：

```yaml
database:
  url: "postgresql://your_username:your_password@localhost:5432/fawen"
```

### 创建数据库

```bash
# PostgreSQL
createdb fawen
```

### 运行数据库迁移

```bash
# 激活虚拟环境后
alembic upgrade head
```

### 注册管理员账号

使用以下命令注册第一个管理员账号：

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "real_name": "系统管理员",
    "department": "技术部"
  }'
```

注册后，需要在数据库中手动将该用户的角色改为 `SYSTEM_ADMIN`：

```sql
UPDATE user_roles 
SET role_id = (SELECT id FROM roles WHERE name = 'SYSTEM_ADMIN')
WHERE user_id = '你的用户ID';
```

或者创建一个初始化脚本。

## 生产环境部署

### 使用 Gunicorn

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 使用 systemd

创建 `/etc/systemd/system/fawen.service` 文件：

```ini
[Unit]
Description=公文文件号管理系统
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/fawen
Environment="PATH=/var/www/fawen/venv/bin"
ExecStart=/var/www/fawen/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl enable fawen
sudo systemctl start fawen
```

### 使用 Nginx 反向代理

创建 `/etc/nginx/sites-available/fawen` 配置文件：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/fawen /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Docker 部署

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: fawen
      POSTGRES_PASSWORD: fawen
      POSTGRES_DB: fawen
    volumes:
      - postgres_data:/var/lib/postgresql/data

  app:
    build: .
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://fawen:fawen@db:5432/fawen
    ports:
      - "8000:8000"
    volumes:
      - ./storage:/app/storage

volumes:
  postgres_data:
```

启动服务：

```bash
docker-compose up -d
```

## 安全建议

1. **修改默认密码**
   - 修改 `config.yaml` 中的 JWT secret key
   - 修改数据库默认密码

2. **启用 HTTPS**
   - 使用 Let's Encrypt 获取免费 SSL 证书
   - 配置 Nginx 启用 HTTPS

3. **配置防火墙**
   - 只开放必要的端口（80, 443, SSH）
   - 限制数据库访问 IP

4. **定期备份**
   - 备份数据库
   - 备份存储的文档

5. **监控日志**
   - 配置日志轮转
   - 设置日志告警

## 故障排查

### 数据库连接失败
检查数据库是否启动：
```bash
sudo systemctl status postgresql
```

检查数据库配置是否正确。

### 权限错误
检查用户角色是否正确分配：
```sql
SELECT u.username, r.name 
FROM users u 
JOIN user_roles ur ON u.id = ur.user_id 
JOIN roles r ON ur.role_id = r.id;
```

### 文件上传失败
检查存储目录权限：
```bash
ls -la storage/
```

确保目录有写入权限。

## 性能优化

1. **数据库优化**
   - 添加适当的索引
   - 定期清理旧数据
   - 配置连接池

2. **缓存优化**
   - 使用 Redis 缓存常用数据
   - 配置 CDN 加速静态资源

3. **代码优化**
   - 使用异步数据库查询
   - 优化查询语句

## 监控

### 健康检查

访问 `/health` 端点检查服务状态：

```bash
curl http://localhost:8000/health
```

### 日志查看

```bash
# 查看应用日志
sudo journalctl -u fawen -f

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```
