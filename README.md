# Everything + FastAPI + Dify Custom Tool 最小可用方案

## 1. 方案目标

把 Windows 上的 `Everything` 搜索能力，包装成一个 `FastAPI` 接口，再作为 `Dify Custom Tool` 导入。

这套方案适合内部部署。

你会得到：

- 一个可启动的 `FastAPI` 服务
- 一个可直接导入 `Dify` 的 `OpenAPI` 示例
- 一个本地 `mock Everything` 服务，方便演示和测试
- 一套完整配置步骤

## 2. 目录结构

```text
.
├── app
│   ├── __init__.py
│   └── main.py
├── examples
│   ├── dify_tool_openapi.json
│   └── mock_everything_server.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## 3. 架构说明

整体链路：

```text
Dify -> FastAPI Bridge -> Everything HTTP Server -> 本地文件索引
```

各层职责：

1. `Everything`
   - 负责建立文件索引
   - 提供本地 HTTP 搜索能力

2. `FastAPI Bridge`
   - 统一参数
   - 控制超时
   - 白名单过滤目录
   - 返回更适合 AI 调用的结果

3. `Dify Custom Tool`
   - 通过 `OpenAPI` 调用 `FastAPI Bridge`

## 4. 最小功能

当前版本提供 3 个接口：

- `GET /`
  - 查看服务入口
- `GET /health`
  - 查看服务状态
  - 可选探测 `Everything` 上游
- `GET /search`
  - 执行文件搜索

## 5. 先决条件

### 5.1 Windows 机器

这台机器负责运行：

- `Everything`
- `FastAPI Bridge`

要求：

- 已安装 `Everything`
- 文件索引已建立
- 机器可被 `Dify` 服务访问

### 5.2 Dify 机器

要求：

- 能访问 `FastAPI Bridge` 的地址
- 能导入 `OpenAPI`

## 6. 配置 Everything

### 6.1 开启 HTTP Server

在 `Everything` 中操作：

1. 打开 `Tools -> Options -> HTTP Server`
2. 勾选 `Enable HTTP server`
3. 设置监听端口，建议 `8080`
4. 设置用户名和密码
5. 取消勾选 `Allow file download`

### 6.2 为什么要关下载

你现在要给 AI 用的是“搜索能力”，不是“文件下载能力”。

关掉下载，更安全。

## 7. 配置 FastAPI Bridge

### 7.1 安装依赖

在项目根目录执行：

```bash
python3 -m pip install -r requirements.txt
```

### 7.2 准备环境变量

复制一份配置：

```bash
cp .env.example .env
```

服务启动时会自动读取项目根目录的 `.env`。

如果你在 Linux 上运行 `FastAPI`，可以直接导出变量：

```bash
export EVERYTHING_BASE_URL="http://127.0.0.1:8080"
export EVERYTHING_USERNAME="admin"
export EVERYTHING_PASSWORD="your-password"
export EVERYTHING_TIMEOUT_SECONDS="10"
export EVERYTHING_DEFAULT_COUNT="10"
export EVERYTHING_MAX_COUNT="50"
export EVERYTHING_ALLOWED_ROOTS="D:\Docs;D:\Projects"
```

如果你在 Windows PowerShell 上运行：

```powershell
$env:EVERYTHING_BASE_URL = "http://127.0.0.1:8080"
$env:EVERYTHING_USERNAME = "admin"
$env:EVERYTHING_PASSWORD = "your-password"
$env:EVERYTHING_TIMEOUT_SECONDS = "10"
$env:EVERYTHING_DEFAULT_COUNT = "10"
$env:EVERYTHING_MAX_COUNT = "50"
$env:EVERYTHING_ALLOWED_ROOTS = "D:\Docs;D:\Projects"
```

### 7.3 环境变量说明

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `EVERYTHING_BASE_URL` | `Everything HTTP Server` 地址 | `http://127.0.0.1:8080` |
| `EVERYTHING_USERNAME` | HTTP 用户名 | `admin` |
| `EVERYTHING_PASSWORD` | HTTP 密码 | `your-password` |
| `EVERYTHING_TIMEOUT_SECONDS` | 上游超时秒数 | `10` |
| `EVERYTHING_DEFAULT_COUNT` | 默认返回条数 | `10` |
| `EVERYTHING_MAX_COUNT` | 单次最大返回条数 | `50` |
| `EVERYTHING_ALLOWED_ROOTS` | 允许返回的目录白名单，分号分隔 | `D:\Docs;D:\Projects` |

### 7.4 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后访问：

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/openapi.json`

## 8. 接口说明

### 8.1 `GET /health`

示例：

```bash
curl "http://127.0.0.1:8000/health"
```

示例返回：

```json
{
  "status": "ok",
  "service": "everything-dify-bridge",
  "everything_base_url": "http://127.0.0.1:8080",
  "default_count": 10,
  "max_count": 50,
  "allowed_roots": [
    "d:\\docs",
    "d:\\projects"
  ],
  "upstream": {
    "reachable": true,
    "total_results": 12345
  }
}
```

### 8.2 `GET /search`

请求示例：

```bash
curl "http://127.0.0.1:8000/search?query=dify&count=5"
```

参数说明：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | `string` | 是 | 搜索词 |
| `count` | `integer` | 否 | 返回条数 |
| `regex` | `boolean` | 否 | 是否启用正则 |
| `case_sensitive` | `boolean` | 否 | 是否区分大小写 |
| `whole_word` | `boolean` | 否 | 是否整词匹配 |
| `path_match` | `boolean` | 否 | 是否按完整路径匹配 |
| `sort` | `string` | 否 | `name`、`path`、`size`、`date_modified` |
| `ascending` | `boolean` | 否 | 是否升序 |

示例返回：

```json
{
  "query": "dify",
  "returned_results": 1,
  "upstream_returned_results": 1,
  "upstream_total_results": 1,
  "filtered_out_by_allowed_roots": 0,
  "count_limit": 5,
  "sort": "name",
  "ascending": true,
  "items": [
    {
      "type": "file",
      "name": "dify-guide.md",
      "path": "D:\\Docs",
      "full_path": "D:\\Docs\\dify-guide.md",
      "size": 2048,
      "date_modified": "2026-05-14T00:00:00Z"
    }
  ]
}
```

## 9. 导入 Dify Custom Tool

### 9.1 方式一：直接导入运行中的 `OpenAPI`

如果你的服务已启动，可直接把这个地址导入 `Dify`：

```text
http://YOUR_FASTAPI_HOST:8000/openapi.json
```

### 9.2 方式二：导入示例文件

仓库已提供：

```text
examples/dify_tool_openapi.json
```

使用前把里面的：

```text
http://YOUR_FASTAPI_HOST:8000
```

改成你的真实地址。

### 9.3 Dify 中的操作步骤

1. 进入 `Tools`
2. 选择 `Custom Tool`
3. 选择通过 `OpenAPI` 导入
4. 填入 `openapi.json` 地址，或上传 `examples/dify_tool_openapi.json`
5. 导入后启用 `searchFiles`

### 9.4 在 Agent 中的提示词建议

可以加一条简单约束：

```text
当用户要求搜索文件、文档、目录、表格、图片时，优先调用 searchFiles。
如果用户没有给出条数，默认取 5 条。
如果返回结果为空，明确告诉用户没有命中，不要编造文件。
```

## 10. 本地演示与测试

如果你当前机器没有安装 `Everything`，可以用仓库里的模拟服务演示整条链路。

### 10.1 启动 mock Everything

```bash
python3 examples/mock_everything_server.py --host 127.0.0.1 --port 18080
```

### 10.2 指向 mock 服务

```bash
export EVERYTHING_BASE_URL="http://127.0.0.1:18080"
export EVERYTHING_ALLOWED_ROOTS="D:\Docs;D:\Projects"
```

### 10.3 启动 FastAPI

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 10.4 验证接口

```bash
curl "http://127.0.0.1:8000/health"
curl "http://127.0.0.1:8000/search?query=dify&count=5"
curl "http://127.0.0.1:8000/search?query=plan&count=5"
```

## 11. 安全建议

至少做这几项：

1. `Everything HTTP Server` 开账号密码
2. 关闭文件下载
3. `FastAPI` 只开放给内网
4. 通过 `EVERYTHING_ALLOWED_ROOTS` 限制目录
5. 反向代理层再加一层鉴权
6. 记录访问日志

## 12. 常见问题

### 12.1 `health` 返回 `degraded`

说明 `FastAPI` 已启动，但连不上 `Everything`。

检查：

1. `Everything` 是否正在运行
2. `HTTP Server` 是否已开启
3. 端口是否正确
4. 用户名密码是否正确

### 12.2 搜得到结果，但被过滤掉

说明命中结果不在 `EVERYTHING_ALLOWED_ROOTS` 内。

你要检查白名单是否配置正确。

### 12.3 Dify 导入失败

先直接打开：

```text
http://YOUR_FASTAPI_HOST:8000/openapi.json
```

如果浏览器打不开，Dify 也导不进去。

## 13. 后续可扩展项

如果你后面要继续做，我建议按这个顺序加：

1. 增加 `file_type` 过滤
2. 增加目录搜索专用接口
3. 增加结果摘要字段
4. 增加访问日志与调用审计
5. 改造成 `MCP Server`

## 14. 自检清单

- [x] 提供完整代码
- [x] 提供 `OpenAPI` 示例
- [x] 提供 `Dify` 导入步骤
- [x] 提供本地测试方法
- [x] 提供安全注意事项
