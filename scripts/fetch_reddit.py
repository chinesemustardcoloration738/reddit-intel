#!/usr/bin/env python3
"""
fetch_reddit.py — reddit-intel skill 数据抓取脚本

用法：
  python3 fetch_reddit.py --query "关键词" [选项]

选项：
  --query     搜索关键词（必填）
  --logic     AND 或 OR（默认 OR）
  --limit     抓取数量（默认 50，最多 200）
  --time      时间范围：week / month / year / all（默认 month）
  --subreddit 限定版块，如 entrepreneur（可选）
  --output    输出文件路径（默认 posts_raw.json）

优先使用公开 JSON API（无需账号）。
如果设置了环境变量 REDDIT_CLIENT_ID 和 REDDIT_CLIENT_SECRET，
则自动切换到 PRAW（更稳定，速率限制更宽松）。
"""

import sys
import json
import time
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("错误：需要安装 requests 库\n运行：pip install requests")
    sys.exit(1)


# ── 配置常量 ──────────────────────────────────────────────────────────
MIN_UPVOTES = 0          # 最低点赞数过滤（0=不过滤）
MIN_BODY_LENGTH = 0      # 最短正文字符数（0=不过滤，允许仅标题帖）
COMMENT_FETCH_LIMIT = 3  # 每帖抓取的热评数量
REQUEST_DELAY = 1.5      # 请求间隔（秒），避免触发限流
MAX_COMMENTS_DELAY = 2.0 # 抓评论时的请求间隔

HEADERS = {
    'User-Agent': 'reddit-intel-skill/1.0 (claude-code-skill; research use)'
}


# ── 工具函数 ──────────────────────────────────────────────────────────

def ts_to_date(utc_ts):
    """Unix 时间戳转 YYYY-MM-DD 字符串。"""
    try:
        return datetime.fromtimestamp(float(utc_ts), tz=timezone.utc).strftime('%Y-%m-%d')
    except (ValueError, TypeError, OSError):
        return ''


def build_query(keywords, logic):
    """根据关键词列表和逻辑构建 Reddit 搜索查询字符串。"""
    parts = [k.strip() for k in keywords if k.strip()]
    if not parts:
        return ''
    if logic.upper() == 'AND':
        return ' '.join(parts)
    else:
        if len(parts) == 1:
            return parts[0]
        return ' OR '.join(f'"{p}"' if ' ' in p else p for p in parts)


def is_valid_post(post):
    """过滤低质量帖子（纯图片/视频且无文字内容）。"""
    # 过滤被删帖
    if post.get('removed_by_category'):
        return False
    title = (post.get('title') or '').strip()
    body = (post.get('selftext') or '').strip()
    # 标题必须存在
    if not title:
        return False
    # 被删除或已移除的正文
    if body in ('[deleted]', '[removed]', ''):
        body = ''
    # 纯图片/视频帖（无文字正文）也保留，因为标题本身可能有价值
    # 只过滤掉完全没有内容的帖子（极少数）
    is_gallery = post.get('is_gallery', False)
    post_hint = post.get('post_hint', '')
    # 纯图片且无标题意义的帖子过滤（标题只有链接或极短）
    if is_gallery and len(title) < 5 and not body:
        return False
    return True


def deduplicate(posts):
    """按帖子 ID 去重。"""
    seen = set()
    result = []
    for p in posts:
        pid = p.get('id')
        if pid and pid not in seen:
            seen.add(pid)
            result.append(p)
    return result


# ── JSON API 抓取（无需账号） ─────────────────────────────────────────

def fetch_via_json_api(query, time_filter, limit, subreddit=None):
    """使用 Reddit 公开 JSON API 搜索帖子。"""
    posts = []
    after = None
    fetched = 0
    batch_size = min(100, limit)

    base = f"https://www.reddit.com/r/{subreddit}/search.json" if subreddit else \
           "https://www.reddit.com/search.json"

    while fetched < limit:
        params = {
            'q': query,
            't': time_filter,
            'limit': min(batch_size, limit - fetched),
            'sort': 'relevance',
            'type': 'link',
        }
        if subreddit:
            params['restrict_sr'] = '1'
        if after:
            params['after'] = after

        try:
            resp = requests.get(base, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 429:
                print("  ⚠️  触发限流，等待 30 秒后重试...")
                time.sleep(30)
                continue
            if resp.status_code != 200:
                print(f"  ⚠️  API 返回 {resp.status_code}，停止抓取")
                break
            data = resp.json()
        except requests.RequestException as e:
            print(f"  ⚠️  网络错误：{e}")
            break
        except json.JSONDecodeError:
            print("  ⚠️  返回内容解析失败")
            break

        children = data.get('data', {}).get('children', [])
        if not children:
            break

        for child in children:
            p = child.get('data', {})
            posts.append(p)
            fetched += 1
            if fetched >= limit:
                break

        after = data.get('data', {}).get('after')
        if not after:
            break

        time.sleep(REQUEST_DELAY)

    return posts


# ── PRAW 抓取（需要 API 凭证） ────────────────────────────────────────

def fetch_via_praw(query, time_filter, limit, subreddit=None):
    """使用 PRAW 官方库搜索帖子（需要环境变量配置）。"""
    try:
        import praw
    except ImportError:
        print("  ⚠️  未安装 praw，回退到 JSON API")
        return None

    client_id = os.environ.get('REDDIT_CLIENT_ID')
    client_secret = os.environ.get('REDDIT_CLIENT_SECRET')

    if not client_id or not client_secret:
        return None

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent='reddit-intel-skill/1.0'
    )

    raw_posts = []
    try:
        target = reddit.subreddit(subreddit) if subreddit else reddit.subreddit('all')
        results = target.search(query, sort='relevance', time_filter=time_filter, limit=limit)
        for submission in results:
            raw_posts.append({
                'id': submission.id,
                'title': submission.title,
                'selftext': submission.selftext,
                'url': f"https://reddit.com{submission.permalink}",
                'score': submission.score,
                'num_comments': submission.num_comments,
                'subreddit': f"r/{submission.subreddit.display_name}",
                'created_utc': submission.created_utc,
                '_praw_obj': submission,
            })
    except Exception as e:
        print(f"  ⚠️  PRAW 搜索失败：{e}")
        return None

    return raw_posts


# ── 抓取评论 ──────────────────────────────────────────────────────────

def fetch_top_comments(post_id, post_url=None, praw_obj=None):
    """抓取帖子的前 N 条高赞评论。"""
    comments = []

    # 优先用 PRAW 对象（如果有）
    if praw_obj:
        try:
            praw_obj.comments.replace_more(limit=0)
            top = sorted(praw_obj.comments.list()[:20],
                         key=lambda c: getattr(c, 'score', 0), reverse=True)
            for c in top[:COMMENT_FETCH_LIMIT]:
                body = getattr(c, 'body', '').strip()
                if body and body not in ('[deleted]', '[removed]'):
                    comments.append({
                        'body': body,
                        'upvotes': getattr(c, 'score', 0)
                    })
            return comments
        except Exception:
            pass  # 回退到 JSON API

    # 用 JSON API 抓评论
    url = f"https://www.reddit.com/comments/{post_id}.json?limit=10&sort=top"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return comments
        data = resp.json()
        if len(data) < 2:
            return comments
        children = data[1].get('data', {}).get('children', [])
        for child in children[:COMMENT_FETCH_LIMIT + 5]:  # 多抓一些再筛
            c = child.get('data', {})
            body = (c.get('body') or '').strip()
            if body and body not in ('[deleted]', '[removed]') and c.get('kind') != 'more':
                comments.append({
                    'body': body,
                    'upvotes': c.get('score', 0)
                })
            if len(comments) >= COMMENT_FETCH_LIMIT:
                break
    except (requests.RequestException, json.JSONDecodeError, IndexError):
        pass

    time.sleep(MAX_COMMENTS_DELAY)
    return comments


# ── 格式化帖子数据 ────────────────────────────────────────────────────

def format_post(raw, comments):
    """将原始 API 数据整理成统一格式。"""
    post_id = raw.get('id', '')
    title = (raw.get('title') or '').strip()
    body = (raw.get('selftext') or '').strip()
    if body in ('[deleted]', '[removed]'):
        body = ''

    # 兼容 PRAW 格式和 JSON API 格式
    url = raw.get('url') or f"https://www.reddit.com/r/{raw.get('subreddit', '')}/comments/{post_id}/"
    if not url.startswith('http'):
        url = f"https://www.reddit.com{url}"

    subreddit_raw = raw.get('subreddit') or raw.get('subreddit_name_prefixed', '')
    if subreddit_raw and not subreddit_raw.startswith('r/'):
        subreddit_raw = f"r/{subreddit_raw}"

    return {
        'id': post_id,
        'title': title,
        'body': body,
        'url': url,
        'upvotes': int(raw.get('score', 0) or 0),
        'num_comments': int(raw.get('num_comments', 0) or 0),
        'subreddit': subreddit_raw,
        'created_utc': raw.get('created_utc', 0),
        'created_date': ts_to_date(raw.get('created_utc', 0)),
        'top_comments': comments,
    }


# ── 主程序 ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Reddit 帖子抓取脚本')
    parser.add_argument('--query', required=True, help='搜索关键词（逗号分隔多个）')
    parser.add_argument('--logic', default='OR', choices=['AND', 'OR'], help='多关键词逻辑')
    parser.add_argument('--limit', type=int, default=50, help='抓取数量（默认50）')
    parser.add_argument('--time', default='month',
                        choices=['week', 'month', 'year', 'all'], help='时间范围')
    parser.add_argument('--subreddit', default=None, help='限定版块（可选）')
    parser.add_argument('--output', default='posts_raw.json', help='输出文件路径')
    args = parser.parse_args()

    limit = min(args.limit, 200)
    keywords = [k.strip() for k in args.query.split(',') if k.strip()]
    query_str = build_query(keywords, args.logic)

    print(f"\nReddit Intel — 数据抓取")
    print(f"  关键词：{keywords}  逻辑：{args.logic}")
    print(f"  查询字符串：{query_str}")
    print(f"  时间范围：{args.time}  目标数量：{limit}")
    if args.subreddit:
        print(f"  限定版块：r/{args.subreddit}")

    # 检测是否有 PRAW 凭证
    use_praw = bool(os.environ.get('REDDIT_CLIENT_ID') and os.environ.get('REDDIT_CLIENT_SECRET'))
    if use_praw:
        print("  模式：PRAW（检测到 API 凭证）")
    else:
        print("  模式：公开 JSON API（无需账号）")

    print("\n开始抓取...")

    # 抓取帖子
    raw_posts = None
    praw_map = {}  # post_id -> praw_obj（用于评论抓取）

    if use_praw:
        raw_posts = fetch_via_praw(query_str, args.time, limit, args.subreddit)
        if raw_posts:
            for p in raw_posts:
                if '_praw_obj' in p:
                    praw_map[p['id']] = p.pop('_praw_obj')

    if not raw_posts:
        raw_posts = fetch_via_json_api(query_str, args.time, limit, args.subreddit)

    print(f"  抓取原始帖子：{len(raw_posts)} 条")

    # 过滤
    valid_posts = [p for p in raw_posts if is_valid_post(p)]
    print(f"  过滤后有效帖子：{len(valid_posts)} 条")

    # 去重
    valid_posts = deduplicate(valid_posts)
    print(f"  去重后：{len(valid_posts)} 条")

    if not valid_posts:
        print("\n⚠️  未找到符合条件的帖子。建议：")
        print("  1. 扩展关键词或改为 OR 逻辑")
        print("  2. 放宽时间范围（改为 year 或 all）")
        print("  3. 去掉版块限制")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump([], f)
        sys.exit(0)

    # 抓取每帖的热评
    print(f"\n抓取热评（每帖前 {COMMENT_FETCH_LIMIT} 条）...")
    formatted_posts = []
    for i, raw in enumerate(valid_posts):
        post_id = raw.get('id', '')
        praw_obj = praw_map.get(post_id)
        comments = fetch_top_comments(post_id, praw_obj=praw_obj)
        formatted_posts.append(format_post(raw, comments))
        print(f"  [{i+1}/{len(valid_posts)}] {raw.get('title', '')[:60]}...")

    # 统计
    subreddits = set(p['subreddit'] for p in formatted_posts if p['subreddit'])
    dates = [p['created_date'] for p in formatted_posts if p['created_date']]
    date_range = f"{min(dates)} 至 {max(dates)}" if dates else "未知"

    # 写出
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_posts, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 抓取完成")
    print(f"  帖子数：{len(formatted_posts)} 条")
    print(f"  来源版块：{len(subreddits)} 个（{', '.join(sorted(subreddits)[:5])}{'...' if len(subreddits) > 5 else ''}）")
    print(f"  时间跨度：{date_range}")
    print(f"  输出文件：{output_path.resolve()}")


if __name__ == '__main__':
    main()
