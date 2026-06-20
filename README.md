# FuFan-OpenClaw

**轻量级、透明的 AI Agent 系统**

FuFan-OpenClaw 是一个基于 Python + Next.js 构建的本地 AI Agent 助手，强调文件即记忆、技能即插件、完全透明的运行机制。

## 核心特色

- **文件即记忆** — 使用 Markdown/JSON 文件管理记忆，拒绝不透明的向量数据库黑盒
- **技能即插件** — 遵循 Anthropic Agent Skills 范式，拖入文件夹即可扩展能力
- **完全透明** — System Prompt 拼接、工具调用、记忆读写全程可视
- **Canvas/A2UI** — Agent 可输出可交互的 HTML，前端实时渲染预览
- **浏览器自动化** — 内置 Browser Use 工具，Agent 可操控浏览器完成网页任务
- **双色主题** — 支持亮色(Bronze)/暗色(Gold)主题切换

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端框架 | Python 3.10+ / FastAPI |
| Agent 引擎 | LangChain 1.x (`create_agent` API) |
| 模型接口 | DeepSeek / OpenAI API 兼容 (OpenRouter, Claude 等) |
| RAG 检索 | LlamaIndex Core (BM25 + 向量混合检索) |
| 浏览器自动化 | browser-use + Playwright |
| 前端框架 | Next.js 14 (App Router) / TypeScript |
| UI 样式 | Tailwind CSS + CSS 自定义属性主题 |
| 代码编辑器 | Monaco Editor |
| 字体 | Space Grotesk |
| 数据存储 | 本地文件系统 (无 MySQL/Redis 依赖) |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 1. 克隆项目

> 注：目前项目并未再GitHub上开源，需要从百度网盘中下载项目完整源码

```bash
git clone <repo-url>
cd mini-OpenClaw
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key（DeepSeek / OpenAI 兼容格式）

# 启动服务
uvicorn app:app --port 8002 --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 即可使用。

### 4. 浏览器自动化 (可选)

如需使用 Browser Use 工具：

```bash
playwright install chromium
```

## 项目结构

```
mini-OpenClaw/
├── backend/
│   ├── app.py                  # FastAPI 入口 (端口 8002)
│   ├── config.py               # 配置加载器
│   ├── .env                    # 环境变量 (API Key 等)
│   ├── api/                    # API 路由
│   │   ├── chat.py             # SSE 流式对话
│   │   ├── sessions.py         # 会话管理
│   │   ├── files.py            # 文件读写
│   │   ├── tokens.py           # Token 统计
│   │   ├── compress.py         # 会话压缩
│   │   └── config_api.py       # RAG 模式配置
│   ├── graph/                  # Agent 状态机
│   │   ├── agent.py            # AgentManager (create_agent API)
│   │   ├── prompt_builder.py   # System Prompt 组装
│   │   ├── session_manager.py  # 会话持久化
│   │   └── memory_indexer.py   # RAG 索引构建
│   ├── tools/                  # 6 个内置工具
│   │   ├── terminal_tool.py    # 命令行执行 (沙箱化)
│   │   ├── python_repl_tool.py # Python 代码执行
│   │   ├── fetch_url_tool.py   # URL 抓取 → Markdown
│   │   ├── read_file_tool.py   # 文件读取 (沙箱化)
│   │   ├── search_knowledge_tool.py  # RAG 知识库检索
│   │   └── browser_use_tool.py # 浏览器自动化
│   ├── workspace/              # System Prompt 组件
│   │   ├── SOUL.md             # Agent 人格与边界
│   │   ├── IDENTITY.md         # Agent 名称与风格
│   │   ├── USER.md             # 用户画像
│   │   └── AGENTS.md           # 操作协议 + Canvas 协议
│   ├── skills/                 # 技能目录 (每个含 SKILL.md)
│   ├── memory/                 # 长期记忆 (MEMORY.md)
│   ├── sessions/               # 会话 JSON 文件
│   └── SKILLS_SNAPSHOT.md      # 技能清单 (自动生成)
│
├── frontend/
│   └── src/
│       ├── app/                # Next.js App Router
│       │   ├── layout.tsx      # 根布局 (主题 + 状态)
│       │   ├── page.tsx        # 对话页面
│       │   ├── memory/         # 记忆管理页面
│       │   └── skills/         # 技能管理页面
│       ├── components/
│       │   ├── layout/         # Header, Sidebar, LearnPanel
│       │   ├── chat/           # ChatPanel, ChatMessage, CanvasPanel 等
│       │   ├── memory/         # MemoryFileList, MemoryEditor 等
│       │   ├── skills/         # SkillLibrary, SkillEditor, SkillStore 等
│       │   └── shared/         # ConfirmDialog 等公共组件
│       └── lib/
│           ├── api.ts          # API 客户端
│           ├── store.tsx       # 全局状态 (React Context)
│           └── theme.tsx       # 主题管理
│
├── CLAUDE.md                   # Claude Code 开发指引
└── Mini-OpenClaw 开发需求文档 (PRD).md
```

## 功能详情

### 对话系统

- SSE 流式响应，实时显示 Agent 思考过程
- 工具调用可视化 (ThoughtChain)，展开/收起查看详情
- 代码块语法高亮 + 一键复制 + 语言标签
- RAG 检索结果卡片展示
- 会话管理：新建、重命名、删除、历史记录
- 会话压缩：对长对话进行摘要压缩，节省 Token

### Canvas/A2UI

Agent 可以生成可交互的 HTML 内容（网页、图表、游戏等），前端在右侧面板中通过 iframe 实时渲染。例如输入"帮我写一个 HTML 贪吃蛇游戏"，Agent 会生成完整的 HTML 并在 Canvas 面板中呈现可玩的游戏。

### 记忆系统

- 基于 Markdown 文件的分层记忆架构
- SOUL.md / IDENTITY.md / USER.md / AGENTS.md — 系统级指令
- MEMORY.md — 跨会话长期记忆
- Monaco 编辑器实时编辑记忆文件
- AI 优化：一键让 AI 帮你整理和优化记忆内容

### 技能系统

- 技能 = SKILL.md 文件 (Markdown 指令，非 Python 函数)
- 技能商店：从 GitHub 浏览和一键安装社区技能
- AI 创建：描述需求，AI 自动生成技能文件
- 文件夹上传：拖入包含 SKILL.md 的文件夹即可添加技能
- 技能启用/禁用/删除管理

### 6 个内置工具

| 工具 | 名称 | 功能 |
|------|------|------|
| 命令行 | `terminal` | 执行 Shell 命令 (沙箱化，危险指令黑名单) |
| Python | `python_repl` | 执行 Python 代码 |
| 网络请求 | `fetch_url` | 抓取 URL 并转换为 Markdown |
| 文件读取 | `read_file` | 读取本地文件 (沙箱化) |
| 知识检索 | `search_knowledge_base` | RAG 混合检索 (BM25 + 向量) |
| 浏览器 | `browser_use` | 浏览器自动化操作 (Playwright) |

### 主题系统

支持亮色/暗色双主题，通过 CSS 自定义属性实现无闪烁切换：

- **亮色主题**：Bronze 强调色 (#B8860B)，Cream 背景 (#fcfaf7)
- **暗色主题**：Gold 强调色 (#D4AF37)，Charcoal 背景 (#121212)

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | SSE 流式对话 |
| GET | `/api/sessions` | 会话列表 |
| POST | `/api/sessions` | 创建会话 |
| PUT | `/api/sessions/{id}` | 重命名会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| GET | `/api/sessions/{id}/history` | 获取会话历史 |
| GET | `/api/sessions/{id}/raw` | 获取原始消息 |
| GET | `/api/tokens/session/{id}` | Token 统计 |
| POST | `/api/sessions/{id}/compress` | 压缩会话 |
| GET/POST | `/api/config` | RAG 模式配置 |
| GET/POST | `/api/files` | 文件读写 |
| DELETE | `/api/skills/{name}` | 删除技能 |

## System Prompt 组装顺序

Agent 的 System Prompt 按以下顺序拼接（每个组件超过 20,000 字符时自动截断）：

1. `SKILLS_SNAPSHOT.md` — 可用技能清单
2. `workspace/SOUL.md` — Agent 人格与行为边界
3. `workspace/IDENTITY.md` — 名称、风格、表情
4. `workspace/USER.md` — 用户画像
5. `workspace/AGENTS.md` — 操作协议 + Canvas 输出协议
6. `memory/MEMORY.md` — 跨会话长期记忆

## 配置

### 环境变量 (.env)

```env
# 模型 API 配置
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 或使用 OpenAI 兼容格式
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### RAG 模式

在前端对话页面点击 RAG 开关即可启用/禁用 RAG 检索增强模式。启用后，Agent 会在回答问题时自动检索 MEMORY.md 中的相关内容。

## 开发

```bash
# 后端热重载开发
cd backend && uvicorn app:app --port 8002 --reload

# 前端开发
cd frontend && npm run dev

# 前端构建
cd frontend && npx next build
```

## 致谢

- [LangChain](https://github.com/langchain-ai/langchain) — Agent 编排引擎
- [LlamaIndex](https://github.com/run-llama/llama_index) — RAG 检索引擎
- [browser-use](https://github.com/browser-use/browser-use) — 浏览器自动化
- [Next.js](https://nextjs.org/) — React 全栈框架
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) — 代码编辑器
- [赋范空间](https://fufan.ai) — FuFan-OpenClaw 项目发起方
