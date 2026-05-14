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

### 9.0 结合你当前环境，先确定地址怎么填

你现在给出的信息是：

- `Dify` 部署目录在 `/root/dify`
- `Dify` 访问 IP 是 `192.168.70.221`
- `Dify` 对外端口是 `80`

所以你进入 `Dify` 后台的地址，应该先按下面这个试：

```text
http://192.168.70.221
```

注意，这个地址是：

**Dify 后台地址**

不是：

**Everything FastAPI Bridge 的地址**

这两个地址不要混掉。

#### 你现在要先判断一件事

`FastAPI Bridge` 准备部署在哪里？

有两种情况：

##### 情况 1：`FastAPI Bridge` 也部署在这台 Dify 服务器上

那你后面导入 `OpenAPI` 时，大概率填：

```text
http://192.168.70.221:8000/openapi.json
```

前提是：

1. 你把 `FastAPI` 跑在这台机器上
2. `8000` 端口已放通
3. 没有被防火墙拦掉

##### 情况 2：`FastAPI Bridge` 部署在另一台机器上

那你后面导入 `OpenAPI` 时，不能填 `192.168.70.221`。

而是要填：

```text
http://你的 FastAPI 机器 IP:8000/openapi.json
```

比如：

```text
http://192.168.70.230:8000/openapi.json
```

#### 这一点最关键

`Dify` 在 `192.168.70.221:80`，只决定你从哪里登录 Dify 后台。

它**不自动等于**你的 `OpenAPI` 地址。

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

这一节按“你现在就要操作”的方式写。

你只要照着点。

#### 第 1 步：先确认 Dify 能访问你的 FastAPI

先在浏览器里打开：

```text
http://YOUR_FASTAPI_HOST:8000/openapi.json
```

按你当前环境，如果 `FastAPI Bridge` 和 `Dify` 在同一台机器，先直接试：

```text
http://192.168.70.221:8000/openapi.json
```

如果浏览器能打开，继续下一步。

如果打不开，先不要进 Dify。

先排查：

1. `FastAPI` 服务是否启动
2. `8000` 端口是否放通
3. `YOUR_FASTAPI_HOST` 是否是 Dify 机器能访问的内网地址
4. 反向代理是否拦截

#### 第 2 步：进入 Dify 工具页

在 Dify 后台按下面顺序操作：

1. 浏览器打开：

```text
http://192.168.70.221
```

2. 登录 Dify
3. 进入工作区
4. 在左侧菜单找到 `Tools`
5. 进入工具页后，找到 `Custom Tool`

如果你打开 `http://192.168.70.221` 进不去，再排查：

1. `docker-compose` 里的 `nginx` 是否正常启动
2. 服务器 `80` 端口是否放通
3. 是否有内网 ACL 或安全组限制

原来的操作顺序是：

1. 登录 Dify
2. 进入工作区
3. 在左侧菜单找到 `Tools`
4. 进入工具页后，找到 `Custom Tool`

如果你的 Dify 版本界面略有不同，名字可能是：

- `Tools`
- `Tool Provider`
- `Custom Tool`
- `Create Custom Tool`

核心目标不变：

**进入自定义工具导入页面。**

#### 第 3 步：选择 `OpenAPI` 导入

在 `Custom Tool` 页面里：

1. 点击 `Create Custom Tool`、`Add Tool` 或类似按钮
2. 选择 `Import from OpenAPI`
3. 进入导入表单

一般会看到两种导入方式：

- 通过 URL 导入
- 通过文件上传导入

#### 第 4 步：推荐用 URL 导入

如果你的 `FastAPI` 服务已经能从 Dify 所在机器访问，优先用 URL。

填写方式：

| 字段 | 填什么 |
| --- | --- |
| `Schema URL` / `OpenAPI URL` | `http://YOUR_FASTAPI_HOST:8000/openapi.json` |
| 名称 | `Everything Search` |
| 描述 | `搜索内部文件索引，返回文件名、路径、修改时间和大小` |

如果你的 `FastAPI Bridge` 就跑在 `192.168.70.221` 这台机器上，可以直接填：

| 字段 | 直接填这个 |
| --- | --- |
| `Schema URL` / `OpenAPI URL` | `http://192.168.70.221:8000/openapi.json` |
| 名称 | `Everything Search` |
| 描述 | `搜索内部文件索引，返回文件名、路径、修改时间和大小` |

填完后点击：

- `Import`
- `Parse`
- `Next`

不同版本按钮名字可能不同。

#### 第 5 步：如果 URL 导入失败，改用文件上传

如果你用 URL 导入失败，就用仓库里的这个文件：

```text
examples/dify_tool_openapi.json
```

先把文件里的地址：

```text
http://YOUR_FASTAPI_HOST:8000
```

替换成真实地址。

然后在 Dify 导入页：

1. 选择 `Upload file`
2. 上传改好的 `examples/dify_tool_openapi.json`
3. 点击导入

#### 第 6 步：核对 Dify 识别出的工具

导入成功后，Dify 一般会识别出两个接口：

1. `healthCheck`
2. `searchFiles`

你重点要用的是：

```text
searchFiles
```

核对这几个点：

- 工具名是 `searchFiles`
- `query` 是必填参数
- `count`、`sort`、`ascending` 是可选参数
- 方法是 `GET`
- 路径是 `/search`

如果这里识别不对，先不要继续。

回头检查：

1. `openapi.json` 是否是最新版本
2. Dify 读取到的是否是旧缓存
3. 地址是否写错

#### 第 7 步：保存并启用工具

在导入结果页：

1. 点击 `Save`
2. 点击 `Enable`
3. 确认 `searchFiles` 处于启用状态

如果页面支持单独开关，建议：

- `healthCheck` 可开可不开
- `searchFiles` 必须开启

#### 第 8 步：把工具挂到 Agent 或 Chatflow

如果你要在 Agent 里用：

1. 回到 `Studio`
2. 打开你的 Agent 应用
3. 找到 `Tools`
4. 勾选 `Everything Search` 或你刚导入的工具名
5. 确认里面的 `searchFiles` 已启用

如果你要在 Workflow / Chatflow 里用：

1. 打开对应应用
2. 添加 `Tool` 节点，或进入 `Agent` 节点
3. 选择刚才导入的 `Everything Search`
4. 选择 `searchFiles`

#### 第 9 步：给 Agent 写一段可直接用的提示词

把下面这段直接放进系统提示词，或角色提示词：

```text
你可以调用 searchFiles 搜索内部文件索引。
当用户提到文件、文档、表格、目录、资料、图片、合同、方案、说明书时，优先尝试调用 searchFiles。
如果用户没有指定返回条数，count 默认使用 5。
如果没有结果，直接告诉用户未找到，不要编造文件。
回答时优先展示文件名和完整路径。
```

#### 第 10 步：在 Dify 里做第一次验证

进入 Agent 的调试页，直接输入：

```text
帮我搜索 dify 相关文件
```

如果工具调用正常，你应该看到：

1. Agent 触发了 `searchFiles`
2. 请求里带上了 `query`
3. 返回结果里有 `items`
4. Agent 最终回答里引用了文件名或路径

#### 第 11 步：如果 Agent 不调用工具，直接这样改

这是最常见问题。

处理方法：

1. 检查工具是否真正绑定到当前应用
2. 检查 `searchFiles` 是否启用
3. 在系统提示词里明确写“优先调用 `searchFiles`”
4. 用更明确的测试句子，不要太抽象

建议测试句子：

```text
搜索文件名里包含 dify 的文件
```

```text
帮我找 plan 相关表格文件
```

```text
搜索 Design 目录
```

#### 第 12 步：如果工具报错，按报错位置排查

##### 情况 A：Dify 里导入就失败

检查：

1. `http://YOUR_FASTAPI_HOST:8000/openapi.json` 能否从 Dify 所在网络访问
2. `openapi.json` 是否返回 `200`
3. 是否被网关、认证、证书拦截
4. 如果你填的是 `http://192.168.70.221:8000/openapi.json`，确认这台机器上确实已经启动 `FastAPI Bridge`

##### 情况 B：导入成功，但调用时报错

先手工执行：

```bash
curl "http://YOUR_FASTAPI_HOST:8000/search?query=dify&count=5"
```

如果这个命令都失败，问题不在 Dify，在你的 `FastAPI` 或 `Everything`。

##### 情况 C：FastAPI 正常，但没有结果

检查：

1. `Everything` 是否索引到目标目录
2. `EVERYTHING_ALLOWED_ROOTS` 是否把结果过滤掉
3. 搜索词是否过窄

#### 第 13 步：建议你真正上线时这样配

推荐配置：

1. `Everything HTTP Server` 只开放给内网
2. `FastAPI Bridge` 通过内网域名访问
3. Dify 填内网域名，例如：

```text
http://everything-bridge.company.local/openapi.json
```

4. `EVERYTHING_ALLOWED_ROOTS` 只放业务目录
5. 不要让 Dify 直接访问 `Everything` 原始 HTTP 地址

#### 结合你当前环境，我建议这样落地

最简单的接法有两种：

##### 方案 A：`FastAPI Bridge` 也放到 `192.168.70.221`

你后面在 Dify 里导入：

```text
http://192.168.70.221:8000/openapi.json
```

优点：

- 最好记
- 最少改动
- 不需要多记一台机器

缺点：

- 这台 Dify 服务器还要额外跑一个 `FastAPI` 服务

##### 方案 B：`FastAPI Bridge` 放到独立机器

你后面在 Dify 里导入：

```text
http://FastAPI_IP:8000/openapi.json
```

优点：

- 和 Dify 解耦
- 更方便单独维护

缺点：

- 需要额外打通网络

#### 所以，原部署步骤需要更新的地方

需要更新，但只是这 4 点：

1. `Dify` 登录地址固定成 `http://192.168.70.221`
2. `OpenAPI URL` 要按 `FastAPI` 实际部署位置填写
3. 如果 `FastAPI` 部署在 Dify 同机，示例地址改成 `http://192.168.70.221:8000/openapi.json`
4. 排障时要先分清“Dify 访问失败”还是“FastAPI / OpenAPI 访问失败”

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
