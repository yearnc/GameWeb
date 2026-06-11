# 游戏小站

一个简洁的网页游戏合集，集成 17 款游戏，统一入口、一键启动。

> 狼人杀游戏基于 [yearnc/werewolf](https://github.com/yearnc/werewolf) 项目改造（路径适配、子应用挂载等），原项目已独立开源。

## 快速开始

```bash
cd GameWeb
python start.py
```

浏览器自动打开 `http://127.0.0.1:5000`，主页和所有游戏运行在同一个端口。

## 游戏一览

### 推理竞技

| 游戏 | 路由 | AI | 模式 |
|------|------|-----|------|
| 🐺 狼人杀 | `/werewolf` | LLM 大模型（9人局） | 旁观者 / 挑战者 |
| 🕵️ 谁是卧底 | `/undercover` | LLM 大模型（5人局） | 观战 / 参与 |
| 🐢 海龟汤 | `/turtlesoup` | LLM 大模型（AI裁判） | 单人推理 |
| 📜 成语接龙 | `/idiom` | LLM 大模型 | 单人接龙 |
| 💬 猜词游戏 | `/wordguess` | LLM 大模型 | 单人猜词 |
| 🎨 你画我猜 | `/drawguess` | LLM 大模型 | 单人绘画 |

### 棋牌桌游

| 游戏 | 路由 | AI | 模式 |
|------|------|-----|------|
| ⚪ 围棋 | `/go` | MCTS 蒙特卡洛树搜索 | 观战 / 人机 |
| ⚫ 五子棋 | `/gomoku` | 评分启发式（C++移植） | 观战 / 人机 |
| ＃ 井字棋 | `/tictactoe` | Minimax | 观战 / 人机 |

### 休闲小游戏

| 游戏 | 路由 | 类型 | 操作 |
|------|------|------|------|
| 🧱 俄罗斯方块 | `/tetris` | 经典下落 | 方向键/WASD |
| 🐍 贪吃蛇 | `/snake` | 经典街机 | 方向键/WASD |
| 🔢 2048 | `/game2048` | 数字合并 | 方向键/WASD/滑动 |
| 💣 扫雷 | `/minesweeper` | 推理益智 | 左键揭开/右键标记 |
| 🍬 消消乐 | `/match3` | 三消交换 | 点击相邻方块 |

## 项目结构

```
GameWeb/
├── start.py              # 一键启动脚本
├── app.py                # FastAPI 主应用，统一路由挂载
├── index.html / style.css# 主页（暖色调分区布局）
│
├── werewolf/             # 🐺 狼人杀 — LLM 驱动的 9 人推理
│   ├── web/              #   FastAPI + SSE + 暗黑酒馆UI
│   └── game/             #   游戏逻辑 + AI 玩家 + 提示词
│
├── undercover/           # 🕵️ 谁是卧底 — LLM 驱动的 5 人词语推理
│   ├── webapp/           #   FastAPI + SSE + 群聊UI + 3款随机主题
│   └── core/             #   状态机 + AI + 98组词对
│
├── turtlesoup/           # 🐢 海龟汤 — AI 裁判问答推理
│   ├── webapp/           #   FastAPI + SSE + 聊天UI
│   └── core/             #   状态机 + AI裁判 + 22个故事
│
├── idiom/                # 📜 成语接龙 — 水墨风 LLM 对战
│   ├── webapp/           #   FastAPI + SSE + 聊天UI
│   └── core/             #   LLM 判断 + 出题
│
├── wordguess/            # 💬 猜词游戏 — 活力橙 LLM 主持
│   ├── webapp/           #   FastAPI + SSE + 聊天UI
│   └── core/             #   LLM 提示 + 判断
│
├── drawguess/            # 🎨 你画我猜 — 工作室风绘画
│   ├── webapp/           #   FastAPI + SSE + Canvas + 聊天UI
│   └── core/             #   LLM 猜画
│
├── go/                   # ⚪ 围棋 — Canvas + MCTS
├── gomoku/               # ⚫ 五子棋 — Canvas + 评分AI
├── tictactoe/            # ＃ 井字棋 — DOM + Minimax
│
├── tetris/               # 🧱 俄罗斯方块 — Canvas
├── snake/                # 🐍 贪吃蛇 — Canvas
├── game2048/             # 🔢 2048 — DOM + 动画
├── minesweeper/          # 💣 扫雷 — DOM 三难度
└── match3/               # 🍬 消消乐 — Canvas + 动画 + 步数系统
```

## 游戏特色

### 谁是卧底

- **三款随机主题**：线索板 / 终端机 / 机密档案，每次进入随机展示
- **无人知道卧底身份**：包括卧底自己，通过描述找出谁不一样
- **并行投票**：所有 AI 使用 `asyncio.gather` 同时投票
- **98 组词对**：16 个类别

### 海龟汤

- AI 裁判主持游戏，只回答 是/不是/是也不是/与此无关
- 30 次提问机会，可提前提交完整推理
- 22 个经典谜题故事

### 成语接龙

- **水墨书法风** UI，楷体字体 + 宣纸色背景
- AI 出题 + 校验，玩家以最后一字接龙
- 本地检测开头字符 + LLM 判断是否为真实成语

### 猜词游戏

- **活力橙渐变** UI，游戏节目风格
- AI 想好一个词，玩家通过提问和提示来猜
- 发消息立显，不等 LLM 回复

### 你画我猜

- **创意工作室** 紫色调 UI
- Canvas 画布自由绘画，6 种颜色 + 橡皮
- AI 通过画面描述猜测你画了什么

### 棋类游戏

- **围棋**：9×9/13×13/19×19，MCTS AI，完整提子/打劫/计目
- **五子棋**：C++ 评分算法移植，随机开局防固定
- **井字棋**：Minimax 完美博弈，不可战胜
- 默认人机对战，支持观战模式（AI vs AI）

### 休闲小游戏

- **俄罗斯方块**：WASD/方向键，7种方块，等级加速
- **贪吃蛇**：WASD/方向键，按任意方向键开始，速度逐级提升
- **2048**：新方块弹入 + 合并脉冲动画，触屏支持
- **扫雷**：简单/中等/困难三档，右键标旗
- **消消乐**：6色方块，30步限制，3连击+奖励步数，交换滑动+消除闪烁+掉落动画

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端 | FastAPI + Uvicorn |
| 实时通信 | SSE（Server-Sent Events） |
| 模板 | Jinja2 |
| 前端 | 原生 HTML + CSS + JS |
| 渲染 | Canvas 2D / DOM |
| AI | DeepSeek API（OpenAI 兼容） |

## 添加新游戏

**静态小游戏**（Canvas/DOM 自包含）：
1. 创建目录，放入 `index.html`
2. `app.py` 挂载：`app.mount("/游戏名", StaticFiles(..., html=True))`
3. `index.html` 对应分区添加卡片

**后端驱动游戏**（FastAPI 子应用）：
1. 创建 `core/`（逻辑）和 `webapp/`（FastAPI）
2. `app.py` 挂载并添加到 `sys.path`
3. 注意模块名不要冲突（不要用 `web`/`game`）

## TODO

- [ ] 五子棋 AI 升级为 MCTS
- [ ] 围棋 19×19 Web Worker 多线程
- [ ] 谁是卧底支持更多玩家数
- [ ] 断线重连
- [ ] 用户系统 + 对局历史
- [ ] 更多游戏：象棋、国际象棋、德州扑克
