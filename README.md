# reddit-intel

**Turn Reddit into a business intelligence feed — keyword in, formatted Excel out.**

Drop a keyword. Get a spreadsheet where every row tells you what users actually think, what they want, who they're switching to, and what your team should do about it next week.

---

## The problem this solves

Your users are on Reddit talking about your product, your competitors, and the problems your industry hasn't solved yet. You just can't read 300 threads a week.

*reddit-intel* does the reading. Claude classifies intent, detects sentiment, extracts competitors mentioned, surfaces the workarounds people share in comment threads, and writes a one-line action item for every post — output as a color-coded Excel file you can drop directly into your next product review.

---

## Quick demo

```
帮我分析 reddit 上关于 Notion 的讨论，做竞品分析
```

```
scrape reddit for "Binance AND scam" posts from the last month
```

```
reddit 上最近有什么人在讨论加密货币出金的问题？
```

---

## Features

- **No account required.** Uses Reddit's public JSON API (no credentials needed).
- **Multi-sort strategy.** Runs `relevance + hot + new + top` in parallel per subreddit, then deduplicates — expands yield from ~150 to 600–1500 posts per keyword.
- **Deep mode.** Fast mode (posts only, 3–5 min) or deep mode (posts + top 3 comments per post, 10–15 min).
- **10 industry frameworks.** Crypto/Finance · E-commerce · AI/Tech · SaaS · Health · Workplace · Gaming + auto-generated frameworks for any industry.
- **Content quality pre-check.** Image posts, auto-bots, and promo spam are detected first so they don't corrupt your classification stats.
- **18 fields per post.** Content type · Core intent · Main category · Sub-tags · Sentiment · Competitors mentioned · Use case · Comment highlights · Action item · Confidence level + metadata.
- **Bilingual output.** Titles and summaries auto-translated to Chinese, original text preserved.
- **Formatted Excel.** Color-coded sentiment/confidence columns, frozen header, alternating rows, highlighted action items, summary sheet with charts.

---

## ⚠️ Reddit API Limits — Read This First

Reddit tightened its API policy in 2023. These are **platform limits, not tool bugs**:

| Limit | What it means |
|-------|---------------|
| 100 posts per request | Maximum a single API call can return |
| ~250–500 posts per sort | Reddit truncates pagination after a few pages regardless of how many posts exist |
| Time filter ≠ more results | `time=month` changes the ranking window, it does NOT increase the total count |
| Comments are separate requests | Deep mode requires one extra API call per post |
| Rate limit | ~10 req/min unauthenticated — script sleeps 2s between calls automatically |

**Our workaround (multi-sort strategy):**
Running `relevance + hot + new + top` separately per subreddit and deduplicating gives ~600–1500 posts per keyword instead of ~150 from a single query.

Reddit has millions of relevant posts — the API only shows you a small window. This is Reddit's business decision (API monetization, 2023). There is no way around it without paying for enterprise access.

---

## Installation

```bash
git clone https://github.com/carrielabs/reddit-intel.git \
  ~/.claude/skills/reddit-intel
pip install openpyxl
```

Restart Claude Code. The skill is ready.

---

## Usage

### Trigger phrases

```
scrape reddit · reddit analysis · reddit insights · monitor reddit
爬reddit · reddit舆情 · reddit帖子分析 · 分析reddit
reddit监控 · 帮我看看reddit上 · reddit上有什么人说
```

### What Claude asks you

1. **Keywords** — supports `AND`, `OR`, `NOT` (e.g., `"Binance AND withdrawal NOT promotion"`)
2. **Analysis goal** — Brand/product research · Industry monitoring · Custom categories
3. **Time range** — Last 7 days (default) · 30 days · 3 months · 1 year · Custom dates
4. **Post count** — Default 100, max 500
5. **Mode** — Fast (posts only) or Deep (posts + comments)
6. **Subreddits** — Specify or skip for global search; Claude recommends if you're unsure

---

## Output

### Sheet 1 — 舆情数据 (18 columns)

| Column | Field | Notes |
|--------|-------|-------|
| 标题（原文）| Original title | |
| 标题（中文）| Chinese translation | |
| 内容摘要（中文）| Chinese summary | ≤500 chars |
| **内容类型** | Content type | 有效文字 / 图片帖 / 自动播报 / 营销推广 (color-coded) |
| 核心意图 | Core intent | 寻求帮助 / 吐槽发泄 / 经验分享 / 求推荐 / 求平替 / 观点讨论 / 新闻事件 |
| 主分类 | Main category | Framework-specific |
| 子标签 | Sub-tags | Up to 3 tags |
| 情绪 | Sentiment | 正面 / 负面 / 中性 / 混合 (color-coded) |
| 提及竞品/项目 | Competitors mentioned | Only explicitly named in post |
| 使用场景 | Use case | |
| 热评精华 | Top comment highlights | 【解决方案】【反驳】【补充】【共鸣】 labeled |
| 行动点 | Action item | Bold, yellow background |
| 置信度 | Confidence | 高 / 中 / 低 (color-coded) |
| 点赞数 | Upvotes | |
| 评论数 | Comment count | |
| 来源版块 | Subreddit | |
| 发帖时间 | Post date | YYYY-MM-DD |
| 原帖链接 | URL | Clickable link |

### Sheet 2 — 概览 (7 blocks)

1. **基础统计** — Total posts, valid posts, date range, subreddit count + distribution
2. **情绪分布** — Positive/Negative/Neutral/Mixed counts with bar chart
3. **内容质量** — Content type breakdown, low-confidence count
4. **分类分布** — Main category Top 10, core intent distribution
5. **高价值信号** — Top 5 upvoted, Top 5 most commented, Top 3 negative posts
6. **竞品提及** — Competitor mention counts Top 10 (only shown when data exists)
7. **综合行动建议** — 3–5 cross-post insights written by Claude

> All numbers in Sheet 2 are calculated by Python — not estimated by Claude.

---

## Architecture

| Phase | Files loaded | What happens |
|-------|-------------|--------------|
| 1 | `SUBREDDIT_MAP.md` | Parameter confirmation, subreddit recommendation |
| 2 | — | `fetch_reddit.py` — multi-sort scrape, dedup, normalize |
| 3 | `CLASSIFY_RULES.md` + `TRANSLATE_RULES.md` | Batch classify + translate 10 posts at a time |
| 4 | `OUTPUT_SCHEMA.md` | Claude writes action items → `export_excel.py` generates .xlsx |

---

## Requirements

- Claude Code (any version supporting custom skills)
- Python 3.8+
- `openpyxl` — `pip install openpyxl`

No Reddit API credentials required. `requests` is not needed — the script uses Python's built-in `urllib`.

---

## License

MIT
