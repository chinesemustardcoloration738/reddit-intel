# reddit-intel

**把 Reddit 变成商业情报源——关键词进去，格式化 Excel 出来。**

丢一个关键词进去，拿到一张表格，每一行都告诉你：用户真正在想什么、他们想要什么、他们在迁移到哪里，以及你的团队明天应该做什么。

---

## 它在解决什么问题

你知道用户在 Reddit 上谈论你的产品、你的竞品、以及这个行业还没解决的问题。你只是没时间每周读 200 个帖子。

*reddit-intel* 替你读。Claude 分类用户意图、提取被提及的竞品、找出评论区里用户分享的解决方案，并为每条帖子写一行行动点——最终生成一份可以直接递给产品经理的 Excel。

---

## 演示

```
帮我分析 reddit 上关于 Notion 的讨论，做竞品分析
```

```
reddit 上有什么人在讨论从 Figma 迁移到别的工具吗？
```

Skill 走完 4 个阶段——确认参数、抓取帖子和热评、每次 10 条批量打标、生成带两个 Sheet 的格式化 Excel。

---

## 核心特性

- **无需账号。** 默认使用 Reddit 公开 JSON API，零配置即可运行。如果你有 Reddit API 凭证，设置两个环境变量后自动切换到 PRAW，更稳定、限流更宽松。

- **抓帖子，也抓评论。** Reddit 的真正洞察往往在回复里。Skill 自动抓每帖前 3 条高赞评论，并提取其中的解决方案。

- **7 套分类框架。** 产品反馈 · 竞品分析 · 用户痛点 · 购买决策 · 行业趋势 · 社区情绪 · 自定义（用户自定义类别）。

- **每条帖子 10 个字段。** 核心意图 · 主分类 · 子标签 · 情绪 · 提及竞品 · 使用场景 · 热评精华 · 行动点 · 置信度。

- **批处理架构。** Phase 3 每批处理 10 条，避免上下文溢出，200 条大批量也能稳定运行。

- **格式化 Excel 输出。** 情绪和置信度列带颜色编码，表头冻结，隔行变色，行动点高亮，附带概览统计 Sheet。

---

## 安装

### 方式一：克隆到技能目录

```bash
git clone https://github.com/carrielabs/reddit-intel.git \
  ~/.claude/skills/reddit-intel
```

### 方式二：手动复制

下载仓库，将整个文件夹复制到：

```
~/.claude/skills/reddit-intel/
```

重启 Claude Code，技能即可使用。

---

## 安装 Python 依赖

```bash
pip install requests openpyxl

# 可选：使用 Reddit 官方 API（更稳定，限流更宽松）
# pip install praw
```

---

## 使用方式

### 基本用法

```
帮我分析 reddit 上关于 Notion 的讨论
```

```
reddit 上的用户怎么看 Linear 这个产品？做个产品反馈分析
```

```
帮我监控 reddit 上关于"客服差"的 Zendesk 投诉
```

Skill 会询问：
1. 分析目的（选预设框架或自定义）
2. 抓取数量（默认 50 条）
3. 时间范围（默认近 30 天）
4. 是否限定某个版块（可跳过）

### 使用 Reddit API 凭证（可选，更稳定）

```bash
export REDDIT_CLIENT_ID="你的 client_id"
export REDDIT_CLIENT_SECRET="你的 client_secret"
```

获取凭证：[reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → 创建应用 → 类型选 script。

### 触发词

`爬 reddit` · `reddit 舆情` · `reddit 帖子分析` · `分析 reddit` ·
`reddit 监控` · `帮我看看 reddit 上` · `scrape reddit` ·
`reddit analysis` · `reddit insights`

---

## 输出说明

### Excel：Sheet 1「舆情数据」

| 列名 | 说明 |
|------|------|
| 标题（原文）| 帖子原始标题 |
| 标题（中文）| 中文翻译 |
| 内容摘要（中文）| 中文摘要，≤500字 |
| 核心意图 | 寻求帮助 / 吐槽发泄 / 经验分享 / 求推荐 / 求平替 |
| 主分类 | 选定框架下的分类 |
| 子标签 | 最多 3 个子标签 |
| 情绪 | 正面/负面/中性/混合（带颜色编码）|
| 提及竞品 | 帖子中明确提及的品牌名 |
| 使用场景 | 具体环境或功能上下文 |
| 热评精华 | 热评摘要，解决方案标注【解决方案】|
| 行动点 | 一句话行动点（加粗高亮）|
| 置信度 | 高/中/低（带颜色编码）|
| 点赞数 | |
| 评论数 | |
| 来源版块 | r/xxx 格式 |
| 发帖时间 | YYYY-MM-DD |
| 原帖链接 | |

### Excel：Sheet 2「概览」

- 总帖数 / 时间跨度 / 版块数量
- 情绪分布（占比）
- 核心意图分布
- 置信度分布
- 提及最多的竞品 Top 5
- 点赞最高的帖子 Top 5

---

## 架构

| 阶段 | 加载文件 | 做什么 |
|------|----------|--------|
| Phase 1 | 无 | 参数确认 |
| Phase 2 | 无 | 运行 fetch_reddit.py |
| Phase 3 | `CLASSIFY_RULES.md` + `TRANSLATE_RULES.md` | 每批 10 条打标 |
| Phase 4 | `OUTPUT_SCHEMA.md` | 运行 export_excel.py 生成 Excel |

---

## 环境要求

- Claude Code（任意支持自定义技能的版本）
- Python 3.8+
- `requests` 和 `openpyxl`（`pip install requests openpyxl`）
- `praw`（可选，用于 Reddit API 访问）

---

## 已知限制

- Reddit 公开 API 主要返回近一年内的数据，更早的历史数据需要 Reddit API 凭证配合 Pushshift。
- Reddit API 有请求频率限制，脚本内置了延时处理，大批量抓取需要几分钟。
- 纯标题帖（无正文）的分类置信度会标"低"，属正常现象。

---

## 许可证

MIT
