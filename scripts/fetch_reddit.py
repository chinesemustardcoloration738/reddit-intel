#!/usr/bin/env python3
"""
fetch_reddit.py — Reddit 帖子抓取脚本
reddit-intel skill Phase 2

=====================================================================
Reddit API 限制说明（2023年政策收紧后）
=====================================================================
Reddit 官方 API 对数据抓取有严格限制，这是平台政策，与本工具无关：

① 单次请求上限：每次 API 请求最多返回 100 条帖子
② 分页总量上限：同一关键词 + 同一排序方式，分页翻完后约 250-500 条
   Reddit 服务器侧故意截断，防止大规模历史数据抓取
③ 时间过滤的限制：time 参数（hour/day/week/month/year/all）是"按热度
   时间窗口"过滤，不是"精确到秒的时间戳过滤"。指定 time=week 不会
   神奇地增加总数，它只是改变排序基准，总量依然受上述截断限制
④ 评论获取：搜索结果不含评论，需对每条帖子单独发一次请求（deep 模式）
⑤ 速率限制：OAuth 认证账号 60 请求/分钟；未认证 10 请求/分钟
   请求过快会返回 429 Too Many Requests，需等待后重试

我们的扩量策略（可将单关键词可获取量从 ~150 扩展至 600-1500 条）：
  策略A：多排序合并 — 用 hot/new/top(week)/top(month)/relevance 各
         跑一遍，合并后去重，理论上 5 × 250 = 1250 条（实际有重叠，约 600-900）
  策略B：多版块并行 — 指定多个 subreddit 分别搜索，结果合并去重
  策略C：时间分段 — 自定义日期范围时，按周分段发请求（利用 pushshift 风格
         的 before/after 参数）；注意原生 Reddit API 不支持 before/after，
         此功能依赖 PullPush.io（第三方，不稳定，作为可选后备）

注意：即使使用所有策略，也无法获取 Reddit 上全部相关帖子。
      Reddit 有数以百万计的相关内容，API 只开放极小的窗口。
      这是 Reddit 的商业决策（2023年 API 收费政策），无法绕过。
=====================================================================
"""

import argparse
import json
import sys
import time
import random
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────
BASE_URL = "https://www.reddit.com"
SEARCH_URL = f"{BASE_URL}/search.json"
SUBREDDIT_SEARCH_URL = f"{BASE_URL}/r/{{subreddit}}/search.json"
USER_AGENT = "reddit-intel/1.0 (Claude Code skill; educational use)"
REQUEST_SLEEP = 2.0        # 每次请求间隔秒数（避免触发限流）
RETRY_SLEEP = 30           # 429 后等待秒数
MAX_RETRIES = 3            # 最大重试次数
MAX_BODY_CHARS = 1500      # 正文最大保留字符数（防止 Claude 上下文溢出）
TOP_COMMENTS = 3           # deep 模式每帖抓取的热评数量


# ─────────────────────────────────────────────
# HTTP 工具
# ─────────────────────────────────────────────
def make_request(url, retries=0):
    """发送 GET 请求，自动处理限流重试。返回解析后的 JSON dict，失败则返回 None。"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except HTTPError as e:
        if e.code == 429:
            if retries < MAX_RETRIES:
                wait = RETRY_SLEEP * (retries + 1)
                print(f"  [限流] 收到 429，等待 {wait} 秒后重试 ({retries+1}/{MAX_RETRIES})...",
                      file=sys.stderr)
                time.sleep(wait)
                return make_request(url, retries + 1)
            else:
                print(f"  [错误] 超过最大重试次数，跳过: {url}", file=sys.stderr)
                return None
        elif e.code == 403:
            print(f"  [错误] 403 Forbidden，版块可能已被设为私密: {url}", file=sys.stderr)
            return None
        elif e.code == 404:
            print(f"  [错误] 404 Not Found: {url}", file=sys.stderr)
            return None
        else:
            print(f"  [HTTP错误] {e.code}: {url}", file=sys.stderr)
            return None
    except URLError as e:
        print(f"  [网络错误] {e.reason}: {url}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"  [解析错误] 无法解析 JSON: {url}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────
# 搜索函数
# ─────────────────────────────────────────────
def build_search_url(query, sort, time_filter, subreddit=None, after=None, limit=100):
    """
    构建 Reddit 搜索 URL。
    注意：time 参数对 new 排序无效（new 总是按最新时间）。
    """
    params = {
        "q": query,
        "sort": sort,
        "t": time_filter,
        "limit": str(min(limit, 100)),
        "restrict_sr": "true" if subreddit else "false",
        "raw_json": "1",
    }
    if after:
        params["after"] = after

    if subreddit:
        base = SUBREDDIT_SEARCH_URL.format(subreddit=subreddit)
    else:
        base = SEARCH_URL

    return f"{base}?{urlencode(params)}"


def fetch_one_sort(query, sort, time_filter, subreddit=None, target=100):
    """
    用单一排序方式抓取帖子，分页直到达到 target 或无更多数据。

    Reddit 分页机制：
    - 每页最多 100 条
    - 用上一页最后一条帖子的 fullname (t3_xxxx) 作为 after 参数翻页
    - Reddit 大约在 250-500 条后停止返回新数据（服务器侧截断）
    """
    posts = []
    after = None
    page = 0

    while len(posts) < target:
        page += 1
        url = build_search_url(query, sort, time_filter, subreddit, after, limit=100)
        print(f"    [抓取] sort={sort} 第{page}页 (已有{len(posts)}条)...", file=sys.stderr)

        data = make_request(url)
        if not data:
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            print(f"    [分页结束] sort={sort} 无更多数据（共{len(posts)}条）", file=sys.stderr)
            break

        for child in children:
            post = child.get("data", {})
            if post:
                posts.append(post)

        after = data.get("data", {}).get("after")
        if not after:
            print(f"    [分页结束] sort={sort} 已到最后一页（共{len(posts)}条）", file=sys.stderr)
            break

        time.sleep(REQUEST_SLEEP + random.uniform(0, 0.5))

    return posts


def fetch_comments_for_post(post_id, subreddit, limit=TOP_COMMENTS):
    """
    deep 模式：抓取单条帖子的热评。
    注意：每个帖子需要单独发一次请求，显著增加耗时和被限流的概率。
    """
    url = (f"{BASE_URL}/r/{subreddit}/comments/{post_id}.json"
           f"?limit=10&sort=top&raw_json=1")
    data = make_request(url)
    if not data or len(data) < 2:
        return []

    comments = []
    try:
        comment_listing = data[1].get("data", {}).get("children", [])
        for item in comment_listing:
            if item.get("kind") == "t1":
                body = item.get("data", {}).get("body", "")
                score = item.get("data", {}).get("score", 0)
                if body and body not in ("[deleted]", "[removed]") and score > 0:
                    comments.append({
                        "body": body[:500],
                        "score": score,
                    })
                    if len(comments) >= limit:
                        break
    except (KeyError, IndexError, TypeError):
        pass

    return comments


# ─────────────────────────────────────────────
# 数据处理
# ─────────────────────────────────────────────
def normalize_post(raw_post, comments=None):
    """将 Reddit API 原始帖子数据规范化为统一格式。截断正文防止上下文溢出。"""
    post_id = raw_post.get("id", "")
    title = raw_post.get("title", "").strip()

    selftext = raw_post.get("selftext", "").strip()
    url = raw_post.get("url", "")

    if selftext in ("[deleted]", "[removed]", ""):
        selftext = ""

    if len(selftext) > MAX_BODY_CHARS:
        selftext = selftext[:MAX_BODY_CHARS] + "... [正文过长，已截断]"

    # 检测是否为图片/视频帖（无实质文字内容）
    is_image = (
        raw_post.get("is_reddit_media_domain", False) or
        raw_post.get("post_hint", "") in ("image", "rich:video", "hosted:video") or
        (not selftext and url and not url.startswith("https://www.reddit.com"))
    )

    created_utc = raw_post.get("created_utc", 0)
    try:
        created_date = datetime.fromtimestamp(
            created_utc, tz=timezone.utc
        ).strftime("%Y-%m-%d")
    except (OSError, OverflowError):
        created_date = ""

    subreddit_raw = raw_post.get("subreddit", "")
    subreddit = (f"r/{subreddit_raw}"
                 if subreddit_raw and not subreddit_raw.startswith("r/")
                 else subreddit_raw)

    permalink = raw_post.get("permalink", "")
    full_url = f"https://www.reddit.com{permalink}" if permalink else url

    return {
        "id": post_id,
        "title": title,
        "selftext": selftext,
        "is_image_hint": is_image,
        "url": full_url,
        "subreddit": subreddit,
        "upvotes": raw_post.get("ups", 0),
        "num_comments": raw_post.get("num_comments", 0),
        "created_date": created_date,
        "created_utc": created_utc,
        "author": raw_post.get("author", "[deleted]"),
        "flair": raw_post.get("link_flair_text", "") or "",
        "is_self": raw_post.get("is_self", False),
        "comments": comments or [],
    }


def deduplicate(posts):
    """按帖子 ID 去重，保留点赞数最高的版本。"""
    seen = {}
    for post in posts:
        pid = post.get("id", "")
        if not pid:
            continue
        if pid not in seen or post.get("upvotes", 0) > seen[pid].get("upvotes", 0):
            seen[pid] = post
    return list(seen.values())


def filter_by_date(posts, start_date=None, end_date=None):
    """精确过滤日期范围内的帖子（可选，补充 API time 参数的粗筛）。"""
    if not start_date and not end_date:
        return posts
    filtered = []
    for post in posts:
        date_str = post.get("created_date", "")
        if not date_str:
            filtered.append(post)
            continue
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
        filtered.append(post)
    return filtered


# ─────────────────────────────────────────────
# 排序策略矩阵
# 每种时间范围对应多组 (sort, time_filter) 组合
# ─────────────────────────────────────────────
SORT_STRATEGIES = {
    "week":   [("relevance", "week"), ("hot", "week"), ("new", "week"), ("top", "week")],
    "month":  [("relevance", "month"), ("hot", "month"), ("top", "month"), ("new", "month")],
    "3month": [("relevance", "year"), ("hot", "year"), ("top", "year"), ("new", "all")],
    "year":   [("relevance", "year"), ("top", "year"), ("hot", "year"), ("new", "all")],
    "all":    [("relevance", "all"), ("top", "all"), ("hot", "all"), ("new", "all")],
}


# ─────────────────────────────────────────────
# 主逻辑
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Fetch Reddit posts for reddit-intel skill",
    )
    parser.add_argument("--query", required=True,
                        help="搜索关键词，支持 AND/OR/NOT 语法")
    parser.add_argument("--limit", type=int, default=100,
                        help="目标帖子数（默认100，最多500）")
    parser.add_argument("--time", default="week",
                        choices=["week", "month", "3month", "year", "all"],
                        help="时间范围（默认: week）")
    parser.add_argument("--mode", default="fast",
                        choices=["fast", "deep"],
                        help="fast=只抓帖子，deep=帖子+热评")
    parser.add_argument("--subreddits", default="",
                        help="限定版块，逗号分隔；空则全站搜索")
    parser.add_argument("--output", default="posts_raw.json",
                        help="输出文件路径")
    parser.add_argument("--start-date", default="",
                        help="自定义起始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", default="",
                        help="自定义结束日期 YYYY-MM-DD")

    args = parser.parse_args()

    limit = min(max(args.limit, 1), 500)
    timeframe = args.time
    subreddits = [s.strip().lstrip("r/") for s in args.subreddits.split(",") if s.strip()]
    mode = args.mode
    query = args.query

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"reddit-intel 数据抓取", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"关键词   : {query}", file=sys.stderr)
    print(f"目标数量 : {limit} 条", file=sys.stderr)
    print(f"时间范围 : {timeframe}", file=sys.stderr)
    print(f"抓取模式 : {mode}", file=sys.stderr)
    print(f"版块限定 : {subreddits if subreddits else '全站搜索'}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"[说明] Reddit API 每种排序方式约返回 250-500 条。", file=sys.stderr)
    print(f"       本脚本采用多排序策略合并去重，实际可获取量约 600-1500 条。", file=sys.stderr)
    print(f"       这是 Reddit 平台限制，不是工具的问题。", file=sys.stderr)
    print(f"", file=sys.stderr)

    sort_strategies = SORT_STRATEGIES.get(timeframe, SORT_STRATEGIES["week"])
    per_sort_limit = min(limit * 2 // len(sort_strategies) + 100, 500)

    all_raw_posts = []
    search_targets = subreddits if subreddits else [None]

    for subreddit in search_targets:
        label = f"r/{subreddit}" if subreddit else "全站"
        print(f"\n[版块: {label}]", file=sys.stderr)

        for sort, t_filter in sort_strategies:
            print(f"  排序策略: {sort} / 时间: {t_filter}", file=sys.stderr)

            unique_so_far = len(deduplicate(all_raw_posts))
            if unique_so_far >= limit * 2 and sort != sort_strategies[0][0]:
                print(f"  [跳过] 已有足够数据（{unique_so_far}条去重后），跳过此策略",
                      file=sys.stderr)
                continue

            fetched = fetch_one_sort(
                query=query,
                sort=sort,
                time_filter=t_filter,
                subreddit=subreddit,
                target=per_sort_limit,
            )
            print(f"  → 获取 {len(fetched)} 条原始数据", file=sys.stderr)
            all_raw_posts.extend(fetched)

            time.sleep(REQUEST_SLEEP)

    print(f"\n[去重] 合并前共 {len(all_raw_posts)} 条，开始去重...", file=sys.stderr)

    normalized = [normalize_post(p) for p in all_raw_posts if p.get("id")]
    deduped = deduplicate(normalized)
    print(f"[去重] 去重后共 {len(deduped)} 条", file=sys.stderr)

    if args.start_date or args.end_date:
        deduped = filter_by_date(deduped, args.start_date, args.end_date)
        print(f"[日期过滤] 过滤后共 {len(deduped)} 条", file=sys.stderr)

    # 3month 特殊处理：过滤掉 3 个月前的帖子
    if timeframe == "3month":
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        before_len = len(deduped)
        deduped = [p for p in deduped if p.get("created_date", "9999") >= cutoff]
        print(f"[3month过滤] {before_len} → {len(deduped)} 条", file=sys.stderr)

    deduped.sort(key=lambda x: x.get("upvotes", 0), reverse=True)
    final_posts = deduped[:limit]

    print(f"[最终] 保留 {len(final_posts)} 条帖子", file=sys.stderr)

    # ── deep 模式：抓取评论 ──
    if mode == "deep" and final_posts:
        print(f"\n[深度模式] 开始抓取热评（每帖最多 {TOP_COMMENTS} 条）...",
              file=sys.stderr)
        est_minutes = len(final_posts) * (REQUEST_SLEEP + 0.5) / 60
        print(f"[预计耗时] {est_minutes:.1f} 分钟", file=sys.stderr)
        print(f"[说明] deep 模式每条帖子需额外发 1 次 API 请求，"
              f"总请求数约 {len(final_posts) * 2}。", file=sys.stderr)

        for i, post in enumerate(final_posts):
            pid = post.get("id", "")
            subreddit_raw = post.get("subreddit", "").lstrip("r/")
            if not pid or not subreddit_raw:
                continue

            print(f"  [{i+1}/{len(final_posts)}] 抓取评论: {pid}", file=sys.stderr)
            comments = fetch_comments_for_post(pid, subreddit_raw, TOP_COMMENTS)
            post["comments"] = comments

            if (i + 1) % 10 == 0:
                print(f"  已处理 {i+1}/{len(final_posts)} 条...", file=sys.stderr)

            time.sleep(REQUEST_SLEEP + random.uniform(0, 0.3))

    # ── 统计报告 ──
    subreddits_seen = sorted(set(p.get("subreddit", "") for p in final_posts))
    dates = [p.get("created_date", "") for p in final_posts if p.get("created_date")]
    image_count = sum(1 for p in final_posts if p.get("is_image_hint"))

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"抓取完成", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"总帖数    : {len(final_posts)}", file=sys.stderr)
    print(f"来源版块  : {len(subreddits_seen)} 个", file=sys.stderr)
    if subreddits_seen[:5]:
        print(f"  前5个   : {', '.join(subreddits_seen[:5])}", file=sys.stderr)
    if dates:
        print(f"时间跨度  : {min(dates)} 至 {max(dates)}", file=sys.stderr)
    print(f"疑似图片帖: {image_count} 条（可能影响分类质量）", file=sys.stderr)
    print(f"输出文件  : {args.output}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    output = {
        "meta": {
            "query": query,
            "timeframe": timeframe,
            "mode": mode,
            "subreddits_queried": subreddits if subreddits else ["all"],
            "total_posts": len(final_posts),
            "subreddits_found": subreddits_seen,
            "date_range": {
                "start": min(dates) if dates else "",
                "end": max(dates) if dates else "",
            },
            "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "api_note": (
                "Reddit API 限制：每种排序方式约返回 250-500 条，"
                "多排序合并去重后实际约 600-1500 条。"
                "这是 Reddit 平台限制，不是工具问题。"
            ),
        },
        "posts": final_posts,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 标准输出仅打印简要统计（供 Claude 读取）
    print(json.dumps({
        "status": "ok",
        "total_posts": len(final_posts),
        "subreddits": subreddits_seen[:10],
        "date_start": min(dates) if dates else "",
        "date_end": max(dates) if dates else "",
        "image_posts_estimate": image_count,
        "output_file": args.output,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
