# reddit-intel

**Turn Reddit into a business intelligence feed — keyword in, formatted Excel out.**

Drop a keyword. Get a spreadsheet where every row tells you what users actually think, what they want, who they're switching to, and what your team should do about it tomorrow.

---

## The problem this solves

You know your users are on Reddit talking about your product, your competitors, and the problems your industry hasn't solved yet. You just can't read 200 threads a week.

*reddit-intel* does the reading. Claude classifies intent, extracts competitors mentioned, surfaces the workarounds people share in comment threads, and writes a one-line action item for each post — all in an Excel file you can hand directly to your product manager.

---

## Demo

```
帮我分析 reddit 上关于 Notion 的讨论，做竞品分析
```

```
scrape reddit for "linear app" complaints, give me product feedback
```

The skill walks through 4 phases — confirming parameters, fetching posts + top comments, batch-classifying in groups of 10, and generating a formatted Excel with two sheets: raw data and a summary overview.

---

## Features

- **Zero account required.** Uses Reddit's public JSON API by default. If you have Reddit API credentials, set two environment variables and it automatically switches to PRAW for better reliability.

- **Fetches comments, not just posts.** The real insight on Reddit is in the replies. The skill pulls the top 3 comments per post and extracts solution workarounds where they exist.

- **7 classification frameworks.** Product Feedback · Competitor Analysis · User Pain Points · Purchase Decisions · Industry Trends · Community Sentiment · Custom (define your own).

- **10-fields per post.** Core intent · Main category · Sub-tags · Sentiment · Competitors mentioned · Use case/environment · Comment highlights · One-line action item · Confidence level.

- **Batched processing.** Claude processes 10 posts at a time to avoid context overflow — safe to run on 200-post batches.

- **Formatted Excel output.** Color-coded sentiment and confidence columns, frozen header row, alternating row colors, highlighted action items, and a summary sheet with distributions and top-voted posts.

---

## Installation

### Option 1: Clone directly

```bash
git clone https://github.com/carrielabs/reddit-intel.git \
  ~/.claude/skills/reddit-intel
```

### Option 2: Manual

Download the repository and copy the folder to:

```
~/.claude/skills/reddit-intel/
```

Restart Claude Code. The skill is ready.

---

## Install Python dependencies

```bash
pip install requests openpyxl

# Optional: for Reddit API access (more reliable, higher rate limits)
# pip install praw
```

---

## Usage

### Basic usage

```
帮我分析 reddit 上关于 Notion 的讨论
```

```
scrape reddit for "customer support" complaints about Zendesk
```

```
reddit 上有什么人在讨论从 Figma 迁移到别的工具吗？
```

The skill will ask you:
1. Which classification framework to use (or define custom categories)
2. How many posts to fetch (default: 50)
3. Time range (default: last 30 days)
4. Whether to restrict to a specific subreddit (optional)

### With Reddit API credentials (optional, for better reliability)

```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
```

To get credentials: [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → create app → script type.

### Trigger phrases

`scrape reddit` · `reddit analysis` · `reddit insights` · `monitor reddit` ·
`爬 reddit` · `reddit 舆情` · `reddit 帖子分析` · `分析 reddit` ·
`reddit 监控` · `帮我看看 reddit 上`

---

## Output

### Excel: Sheet 1 — 舆情数据

| Column | Description |
|--------|-------------|
| 标题（原文）| Original title |
| 标题（中文）| Chinese translation |
| 内容摘要（中文）| Chinese summary (≤500 chars) |
| 核心意图 | Seeking help / Rant / Sharing / Recommendation / Alternative |
| 主分类 | Category from chosen framework |
| 子标签 | Up to 3 sub-tags |
| 情绪 | 正面 / 负面 / 中性 / 混合 (color-coded) |
| 提及竞品 | Competitor brands explicitly mentioned |
| 使用场景 | Specific environment or context |
| 热评精华 | Top comment highlights, `【解决方案】` marked |
| 行动点 | One-line action item for product/marketing teams |
| 置信度 | 高 / 中 / 低 (color-coded) |
| 点赞数 | Upvotes |
| 评论数 | Comment count |
| 来源版块 | Subreddit |
| 发帖时间 | Post date |
| 原帖链接 | Link to original post |

### Excel: Sheet 2 — 概览

- Total posts, date range, subreddit count
- Sentiment distribution
- Core intent distribution
- Confidence distribution
- Top 5 mentioned competitors
- Top 5 most upvoted posts

---

## Architecture

| Phase | Files loaded | What happens |
|-------|-------------|--------------|
| 1 | None | Parameter confirmation |
| 2 | None | `fetch_reddit.py` — scrape posts + comments |
| 3 | `CLASSIFY_RULES.md` + `TRANSLATE_RULES.md` | Batch classify 10 posts at a time |
| 4 | `OUTPUT_SCHEMA.md` | `export_excel.py` — generate .xlsx |

---

## Requirements

- Claude Code (any version supporting custom skills)
- Python 3.8+
- `requests` and `openpyxl` (install via `pip install requests openpyxl`)
- `praw` (optional, for Reddit API access)

---

## Limitations

- Reddit's public API returns posts from approximately the last 1 year. For older data, Reddit API credentials with Pushshift access are needed.
- Reddit API has rate limits. The script adds delays between requests automatically.
- Classification quality depends on post length — very short posts (title-only) will get a "低" confidence rating.

---

## License

MIT
