# ELA 后端重构说明（backend-temp）

## 1. 重构目标

- 将 `ela-backend` 重构为更清晰的分层架构，提升可维护性与可扩展性。
- 保持与前端 `ela-frontend` 的接口协议兼容，避免联调中断。
- 保留 `localApp/` 作为独立本地程序，不改变其运行方式。

## 2. 重构后目录结构

```text
ela-backend-temp/
  app.py                        # 启动入口
  project_config_TEMPLATE.py    # 配置模板
  requirements.txt              # 依赖清单
  .gitignore                    # Git 忽略规则

  api/                          # HTTP 路由层（控制器）
    __init__.py
    auth_routes.py
    chat_routes.py

  core/                         # 应用核心组件
    __init__.py
    app_factory.py              # 应用工厂
    config.py                   # Flask 配置
    extensions.py               # db/jwt/cors 扩展实例
    responses.py                # 统一响应工具

  database/                     # 数据模型与兼容工具
    __init__.py
    extensions.py               # 兼容导出 db
    models.py                   # ORM 模型与初始化
    dbUtil.py                   # 兼容旧调用入口

  repositories/                 # 数据访问层
    __init__.py
    auth_repository.py
    chat_repository.py
    course_repository.py
    cq_repository.py

  services/                     # 业务服务层
    __init__.py
    auth_service.py
    chat_service.py
    redis_service.py

  util/                         # 通用能力与兼容封装
    __init__.py
    chat.py
    getLlmResponse.py

  routes/                       # 兼容旧导入路径
    __init__.py
    auth_routes.py
    chat_routes.py

  auth/                         # 兼容旧导入路径
    __init__.py
    AuthDataBaseUtil.py

  localApp/                     # 独立本地程序（保持独立）
    questionProcess/
      CQProcessApp.py
      prompts/
      cqFiles/
```

## 3. 分层职责说明

- `api`：只处理请求参数、鉴权、响应结构，不写复杂业务。
- `services`：承载核心业务规则，例如注册校验、会话删除校验、流式回复编排。
- `repositories`：只负责数据库读写，降低业务层与 ORM 的耦合。
- `database`：定义 ORM 模型、数据库初始化与旧接口兼容转发。
- `core`：集中应用配置、扩展初始化与应用工厂。
- `util`：保留 LLM 调用与历史函数名，方便平滑迁移。

## 4. 前后端协同逻辑

前端基地址来自 `ela-frontend/src/shared/api/httpClient.js`，默认 `API_BASE_URL=/api`。  
开发模式下由 Vite 代理到 `http://127.0.0.1:5000`，因此后端需暴露 `/api/*` 路径。

### 4.1 认证链路

- 登录：`POST /api/auth/login`
  - 前端读取 `response.token`、`response.user` 存入 localStorage。
- 注册：`POST /api/auth/register`
- 发送验证码：`POST /api/auth/send-code`
- 检查 ID：`GET /api/auth/check-id?id=xxx`

### 4.2 聊天链路

- 会话列表：`GET /api/chat/windows`
- 会话详情：`GET /api/chat/history?windowID=...`
- 新建会话：`POST /api/chat/create`
- 普通落库：`POST /api/chat/send`
- 流式回复：`POST /api/chat/stream`
- 删除会话：`POST /api/chat/delete-window`

除 `auth` 部分接口外，聊天接口均要求 `Authorization: Bearer <token>`。

## 5. 关键兼容策略

- 保留 `database/dbUtil.py`、`auth/AuthDataBaseUtil.py`、`routes/*.py` 旧路径入口，内部转发到新分层实现。
- 保留 `util/chat.py` 的 `getChatResponse` 函数签名，兼容历史调用。
- 响应主体继续使用 `status/msg/data` 结构，避免前端改动。

## 6. 配置与运行

### 6.1 准备配置

1. 复制 `project_config_TEMPLATE.py` 为 `project_config.py`
2. 填写：
   - `BASE_URL`
   - `API_KEY`
   - `MODEL`
   - `JWT_SECRET_KEY`

可选环境变量：

- `ELA_DATABASE_URI`：数据库连接串（默认 `sqlite:///project.db`）
- `ELA_REDIS_HOST` / `ELA_REDIS_PORT` / `ELA_REDIS_DB`：Redis 连接参数

### 6.2 安装依赖

```bash
pip install -r requirements.txt
```

### 6.3 启动后端

```bash
python app.py
```

默认监听 `127.0.0.1:5000`。

## 7. 后续开发建议

- 新增业务优先落在 `services + repositories`，路由层只做薄控制器。
- 变更接口时先检查前端 `features/auth/api.js` 与 `features/chat/api.js` 的字段依赖。
- 生产环境建议替换 `app.py` 直接启动方式，使用 WSGI/ASGI 进程管理器部署。
