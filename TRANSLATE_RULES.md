# TRANSLATE_RULES.md
## 翻译规范 + 摘要生成规则 — Phase 3 加载

**在 Phase 3 加载。处理标题翻译、内容摘要、热评提炼。**

---

## 一、标题翻译（title_zh）

**翻译原则：**
- 保留原意，不美化，不缩减
- 保留原标题中的情绪色彩（"absolutely furious about X" → "对X彻底愤怒了"，不要翻成"对X不满"）
- 保留专有名词的英文（产品名、公司名、技术术语）
- 如果标题是问句，中文也保留问句形式

**示例：**
- `I switched from Notion to Obsidian after 3 years — here's why`
  → `用了 3 年 Notion 之后我换到了 Obsidian——原因在这里`

- `Anyone else think the new pricing is absolutely insane?`
  → `就我一个人觉得新定价完全离谱吗？`

- `PSA: There's a free workaround for the export limit`
  → `提示：导出限制有个免费绕过方法`

---

## 二、内容摘要（summary_zh）

### 长度规则

| 帖子正文长度 | 摘要处理方式 |
|------------|------------|
| ≤ 150字（英文）/ ≤ 80字（中文） | 全文翻译，不裁剪 |
| 150–500字 | 提炼核心内容，保留关键细节 |
| > 500字 | 提炼为 ≤ 500 中文字的摘要 |
| 无正文（仅标题的帖子） | 标注"【仅标题帖，无正文内容】" |

### 摘要内容要求

摘要必须包含（如果原帖有）：
1. **用户遇到的具体情况**（什么产品/功能/场景）
2. **核心问题或核心观点**（一句话）
3. **具体数据或细节**（如果有，必须保留）
4. **结论或用户的诉求**（如果有）

### 禁止出现在摘要里的内容

- 你对内容的评价（"这是一个很有价值的反馈..."）
- 重复标题的内容
- 过渡语（"帖子主要讲的是..."，"总体而言..."）
- 推断的内容（原帖没有写的，不加进摘要）

### 摘要示例

**原帖正文（英文）：**
> I've been using Notion for my team of 8 people for 3 years. Last month they raised prices from $8/person to $16/person. That's $1,536/year just for our small team. I looked into alternatives and we moved to Obsidian + a shared folder system. It took 2 weekends to migrate but we're saving $800/year and honestly the workflow is better now. The only thing I miss is the database views.

**摘要：**
> 使用 Notion 三年、8人团队，上月涨价从每人 $8 到 $16，全年费用达 $1536。迁移到 Obsidian + 共享文件夹方案，花了两个周末完成迁移，每年节省 $800。认为迁移后工作流反而更好，唯一遗憾是失去了数据库视图功能。

---

## 三、热评精华提炼（top_comments_summary）

### 处理逻辑

1. 抓取最多 3 条高赞评论
2. 判断评论价值类型：

| 类型 | 标注方式 | 条件 |
|------|----------|------|
| 提供解决方案 | 开头加 `【解决方案】` | 给出了可操作的具体解法 |
| 有力反驳 | 开头加 `【反驳】` | 对原帖观点提出有据可查的反对 |
| 补充信息 | 开头加 `【补充】` | 添加了原帖没有的重要信息 |
| 情绪共鸣 | 开头加 `【共鸣】` | 表达同感，无新增信息 |

3. 如果多条评论都是情绪共鸣（无实质内容），合并为一句话："多条评论表达同感，无新增信息。"

4. **无评论时**：留空，不写"暂无评论"或占位符。

### 示例

**评论原文：** "Just export as CSV first, then import to Airtable. The database views are still there, just different UI."

**热评精华：**
`【解决方案】可先导出为 CSV，再导入 Airtable，数据库视图功能保留，只是 UI 不同。`

---

## 四、非英语帖子处理

Reddit 主要是英语社区，但部分版块（如 r/CryptoCurrency）偶有其他语言帖子：

| 原帖语言 | 处理方式 |
|----------|----------|
| 英语 | 正常翻译 |
| 中文 | title_zh 填入原文，summary_zh 填入原文内容，无需翻译 |
| 西班牙语/法语/德语等 | 翻译为中文，title_zh/summary_zh 正常填写 |
| 无法识别的语言 | summary_zh 填入"【非英语帖子，语言无法识别，已跳过翻译】"，置信度标"低" |

---

## 五、翻译质量约束

**不允许出现的翻译问题：**
- 过度正式化（Reddit 是非正式语境，翻译应该保留口语感）
- 情绪稀释（愤怒翻成"不满意"，兴奋翻成"较为满意"）
- 技术术语汉化（`workflow` 保留"工作流"，不要翻成"工作程序"；`plugin` 保留"插件"）
- 删除用户的具体数字和数据

**保留英文的场景：**
- 产品名、应用名：Notion / Obsidian / Airtable / Figma
- 公司名：Google / Microsoft / Anthropic
- 技术术语（如果中文无标准对应）：API / webhook / markdown
- Reddit 专有词汇：subreddit / upvote / AMA
