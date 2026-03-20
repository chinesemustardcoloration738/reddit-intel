# Reddit Intel — 工作流调度器

把关键词丢进去，拿到一份可以直接递给产品经理的 Reddit 舆情 Excel。

---

## 永久约束（任何阶段均有效，不可覆盖）

1. **禁止捏造数据。** 字段无法从原文判断时，留空或填"无法判断"，不推断，不脑补。
2. **批处理是强制的。** Phase 3 每批严格处理 10 条，禁止一次性处理全部帖子。
3. **竞品只提取明确提及的品牌名。** 帖子里没有出现的品牌名，一律不写。
4. **置信度诚实标注。** 文本不足以可靠判断时，强制标"低"，不许为了好看标"高"。
5. **行动点必须具体。** "值得关注""建议持续观察"不是行动点，直接删除，重写。
6. **热评精华基于真实评论内容。** 如果帖子无评论或评论无实质内容，该字段留空。

---

## 触发词

以下任意一种说法都会激活此 Skill：

`scrape reddit` · `reddit analysis` · `reddit insights` · `monitor reddit` ·
`爬 reddit` · `reddit 舆情` · `reddit 帖子分析` · `分析 reddit` ·
`reddit 监控` · `帮我看看 reddit 上` · `reddit 上有什么人说`

---

## Phase 1：参数确认

向用户确认以下参数（可以一次性问完，不要逐条问）：

```
① 关键词是什么？（多个关键词用逗号分隔，默认 OR 逻辑；如需 AND 请说明）
② 分析目的是什么？
   A. 产品反馈   B. 竞品分析   C. 用户痛点
   D. 购买决策   E. 行业趋势   F. 社区情绪   G. 自定义
   → 选 G 则追问：你想分哪几个类别？（3-6个为宜）
③ 抓取数量？（默认 50，最多 200）
④ 时间范围？（默认近 30 天；可选：近 7 天 / 近 3 个月 / 近一年）
⑤ 限定某个 Reddit 版块吗？（可以跳过，跳过则全站搜索）
```

确认完毕后，记录参数，进入 Phase 2。

**参数存储格式（记录在工作记忆中）：**
- QUERY: [关键词字符串，按 Reddit 语法处理]
- LOGIC: [AND / OR]
- LIMIT: [数字]
- TIMEFRAME: [week / month / year / all]
- SUBREDDIT: [版块名 / 空]
- FRAMEWORK: [A-G + 如果是G则附自定义类别列表]

---

## Phase 2：数据抓取

执行以下命令：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/fetch_reddit.py" \
  --query "QUERY" \
  --logic "LOGIC" \
  --limit LIMIT \
  --time TIMEFRAME \
  --output posts_raw.json
```

如果限定版块，追加参数：`--subreddit "版块名"`

**等待脚本完成后：**
1. 读取 `posts_raw.json`
2. 向用户报告：`抓取完成：共 X 条帖子，来自 N 个版块，时间跨度 [最早日期] 至 [最新日期]`
3. 如果 posts_raw.json 为空，或脚本报错，向用户说明并询问是否调整参数重试
4. 进入 Phase 3

---

## Phase 3：批量认知处理

**首先加载：**
```
READ "${CLAUDE_SKILL_DIR}/CLASSIFY_RULES.md"
READ "${CLAUDE_SKILL_DIR}/TRANSLATE_RULES.md"
```

**批处理规则：**
- 读取 posts_raw.json，按顺序每次取 10 条
- 对每批 10 条帖子进行完整处理
- 每批处理完毕后，追加到 posts_processed 列表
- 向用户实时展示进度：`✓ 已处理 X / 总数 Y`
- 全部批次完成后，将完整结果写入 `posts_processed.json`

**每条帖子的处理输出格式（JSON 对象）：**

```json
{
  "id": "帖子ID",
  "title_original": "原始标题",
  "title_zh": "中文标题翻译",
  "summary_zh": "中文内容摘要（≤500字，短帖保留全文，见 TRANSLATE_RULES.md）",
  "core_intent": "核心意图（见 CLASSIFY_RULES.md 的意图列表）",
  "main_category": "主分类标签（来自用户选的框架，见 CLASSIFY_RULES.md）",
  "sub_tags": ["子标签1", "子标签2"],
  "sentiment": "情绪（正面/负面/中性/混合）",
  "competitors_mentioned": ["品牌名1", "品牌名2"],
  "use_case": "使用场景描述（无则留空）",
  "top_comments_summary": "热评精华，含解决方案时标注【解决方案】",
  "action_item": "一句话行动点，具体到产品/市场人员明天能做什么",
  "confidence": "置信度（高/中/低）",
  "upvotes": 0,
  "num_comments": 0,
  "subreddit": "r/xxx",
  "created_date": "YYYY-MM-DD",
  "url": "https://reddit.com/..."
}
```

**写入 posts_processed.json：**
```python
import json
# 将完整的 processed_posts 列表写入文件
with open('posts_processed.json', 'w', encoding='utf-8') as f:
    json.dump(processed_posts, f, ensure_ascii=False, indent=2)
```

---

## Phase 4：生成 Excel

**首先加载：**
```
READ "${CLAUDE_SKILL_DIR}/OUTPUT_SCHEMA.md"
```

**执行命令：**
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/export_excel.py" \
  --input posts_processed.json \
  --keyword "关键词（用于文件名）"
```

**完成后向用户报告：**
```
✅ 完成

文件：reddit_intel_[关键词]_[日期].xlsx
包含：X 条帖子，Y 列数据
路径：[当前工作目录]/reddit_intel_[关键词]_[日期].xlsx

置信度分布：高 X 条 / 中 Y 条 / 低 Z 条（低置信度条目建议人工复核）
```

---

## 文件加载时间表

| 阶段 | 加载文件 | 原因 |
|------|----------|------|
| Phase 1–2 | 无 | 参数确认和抓取不需要提示词 |
| Phase 3 | `CLASSIFY_RULES.md` + `TRANSLATE_RULES.md` | 打标和翻译规则 |
| Phase 4 | `OUTPUT_SCHEMA.md` | Excel 列结构定义 |

---

## 错误处理

**fetch_reddit.py 失败：**
- 网络超时：提示用户检查网络，可缩小抓取数量重试
- 返回 0 条：可能关键词过于冷门或版块限制过严，建议扩展关键词或去掉版块限制

**Phase 3 中途中断：**
- 记录已处理到第几条，告知用户可以恢复
- 不删除已生成的部分结果

**export_excel.py 失败：**
- 检查 posts_processed.json 是否存在且非空
- 检查 openpyxl 是否已安装（`pip install openpyxl`）
