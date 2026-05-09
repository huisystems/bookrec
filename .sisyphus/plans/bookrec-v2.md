# 书籍推荐工具 v2 深度重构计划

## 一、目标

从豆瓣抓取**经管类 + AI类**近期出版（≤12 个月）、评分较高的图书，生成带简介/目录的推荐列表，并将所有数据沉淀到 Obsidian 知识库中，支持增量积累和回溯。

---

## 二、总体架构

```
CLI (click) → Orchestrator → DataSources(豆瓣) → Filter → Ranker → Store(Obsidian) + Output(Markdown)
```

---

## 三、目录结构

```
src/
├── cli/                     # CLI 入口
│   ├── __init__.py
│   └── app.py               # click commands: fetch | recommend | list | search | stats | note
├── data_sources/            # 数据源
│   ├── __init__.py
│   ├── base.py              # BaseDataSource 抽象类
│   ├── douban.py            # 豆瓣数据源（latest + tag 两种策略）
│   └── registry.py          # 数据源注册
├── models/                  # 数据模型
│   ├── __init__.py
│   └── book.py              # Book dataclass（扩展：tags, isbn, price, score_breakdown）
├── services/                # 核心服务
│   ├── __init__.py
│   ├── filter.py            # 筛选（保留+增强）
│   ├── ranker.py            # 排序（保留+扩展"推荐指数"）
│   └── orchestrator.py      # 编排器：抓→筛→排→存→输出
├── knowledge/               # 知识库层
│   ├── __init__.py
│   └── store.py             # ObsidianStore：读写 .md 文件+YAML frontmatter
├── output/                  # 输出格式
│   ├── __init__.py
│   ├── markdown_gen.py      # Markdown 推荐列表（增强）
│   └── formats.py           # JSON/CSV 等
└── core/
    ├── __init__.py
    └── config.py            # 配置（知识库路径、抓取参数等）
```

---

## 四、知识库（Obsidian）设计

### 目录布局

```
<知识库根目录>/
├── 图书/
│   ├── 经管/           # 商业经管类
│   │   ├── 纳瓦尔宝典.md
│   │   └── ...
│   ├── AI/             # 人工智能/AI 类
│   │   ├── 哈萨比斯：谷歌AI之脑.md
│   │   ├── Agent设计模式.md
│   │   └── ...
│   └── __索引.md       # 所有图书汇总表（自动维护）
├── 推荐列表/            # 每次推荐产出
│   ├── 2026-05-TOP10.md
│   └── ...
├── 数据源快照/          # 原始抓取数据（用于追溯）
│   ├── 2026-05-09-经管.json
│   └── 2026-05-09-AI.json
└── 统计.md             # 自动统计总书数/分类分布/评分趋势
```

### 每本书的 .md 格式

```markdown
---
douban_id: "36672955"
title: "哈萨比斯：谷歌AI之脑"
author: "塞巴斯蒂安·马拉比"
publisher: "浙江科学技术出版社"
published: "2026-03"
isbn: "9787571234567"
rating: 8.8
rating_count: 365
category: "AI"
tags:
  - 人工智能
  - 谷歌
  - DeepMind
first_seen: "2026-05-09"
last_recommended: "2026-05-09"
source_url: "https://book.douban.com/subject/36672955/"
---

## 简介

（简介内容）

## 目录

（目录内容）

## 笔记

<!-- 用户可在此写笔记 -->
```

### 去重策略

- key = `douban_id`（豆瓣 subject ID）
- 抓取前检查 `图书/**/*.md` 中 YAML frontmatter 的 `douban_id`
- 已存在的 book 只更新：`last_seen`、`rating`、`rating_count`、`last_recommended`
- 新 book 完整写入

---

## 五、数据源策略

### 5.1 商业经管（Douban Latest）

| 项目 | 内容 |
|---|---|
| URL | `https://book.douban.com/latest?subcat=商业经管` |
| 解析器 | 复用现有 `.chart-dashed-list li.media` 解析 |
| 页数 | 1 页，约 6 本 |
| 日期过滤 | 不需要（页面都是新书） |
| CLI | `bookrec fetch --category 经管` |

### 5.2 AI 类（Douban Tags）

| 项目 | 内容 |
|---|---|
| URL | `https://book.douban.com/tag/人工智能?sort=time` |
|  | `https://book.douban.com/tag/机器学习?sort=time` |
|  | `https://book.douban.com/tag/深度学习?sort=time` |
| 解析器 | 新建 `_parse_tag_item()`，适配 `.subject-item` 结构 |
|  | h2 a → 标题+链接 |
|  | .pub → 作者/出版社/日期（`/` 分隔第 4 段） |
|  | .rating_nums → 评分 |
|  | .pl → 评价人数 |
| 页数 | 多页，每页 20 本 |
| 日期过滤 | **需要**：跳过出版 > 12 个月的书 |
| CLI | `bookrec fetch --category AI` |

### 5.3 经管类补充（Douban Tags）

| 项目 | 内容 |
|---|---|
| URL | `https://book.douban.com/tag/经管?sort=time` |
|  | 可扩展：tag/商业, tag/管理, tag/投资 |
| 解析器 | 同 AI 类 tag 解析器 |
| 日期过滤 | **需要** |

---

## 六、CLI 命令

```
bookrec fetch --category 经管,Ai [--months 12]
  → 抓取指定分类的新书，写入知识库

bookrec recommend [--top 10] [--category 经管,AI] [--min-rating 7.5]
  → 从知识库中筛选+排序，生成推荐列表
  
bookrec list [--category 经管] [--min-rating 8] [--tags 大模型]
  → 浏览知识库中的图书

bookrec search <query>
  → 全文搜索知识库

bookrec note <book-id> <note-text>
  → 给某本书添加笔记

bookrec stats
  → 知识库统计：总数/分类分布/评分趋势

bookrec history
  → 查看历史推荐记录
```

### 命令依赖关系

```
fetch (独立) → 写入知识库
    ↓
recommend（从知识库读取）→ 生成 推荐列表/*.md + 更新图书 YAML
    ↓
list / search / stats / history（只读）
note（写入单本书 YAML）
```

---

## 七、推荐质量（Ranker 增强）

### 当前评分公式
```
score = 0.4 × 评分 + 0.3 × 新鲜度 + 0.3 × 热度
```

### 新增"推荐指数"维度
```
recommendability = 
  0.35 × rating_score      # 评分（反映质量）
  0.20 × recency_score     # 新鲜度
  0.15 × popularity_score  # 热度（评价人数->置信度）
  0.15 × accessibility     # 可读性（科普>教材>论文）
  0.15 × topicality        # 话题性（当前热点）
```

- **可读性**: 出版在商业/大众类 > 学术出版社 > 技术教材
- **话题性**: 关键词匹配当前热议主题（大模型、AGI、AI 创业……）

---

## 八、实施步骤（Phase 1-4）

### Phase 1：基础设施（30min）
- [x] 1.1 重写 Book model：添加 tags、isbn、price、source 字段
- [x] 1.2 创建 ObsidianStore：读写 .md + YAML frontmatter
- [x] 1.3 创建 `core/config.py`：知识库路径等配置
- [x] 1.4 更新 requirements.txt（添加 `click`, `pyyaml`, `rich`）

### Phase 2：数据源重构（1h）
- [x] 2.1 创建 `data_sources/base.py`：BaseDataSource 抽象类
- [x] 2.2 重构 douban.py：
  - [x] newest_books() → 保留原有解析（复用）
  - [x] tag_books() → 新解析器（.subject-item）
  - [x] 详情页抓取 fetch_book_detail() 保留
  - [x] 分页支持（tag 页面）

### Phase 3：Orchestrator + CLI（1h）
- [x] 3.1 创建 orchestrator.py：编排整个流程
- [x] 3.2 创建 CLI app.py：所有 click 命令
- [x] 3.3 更新 filter/ranker：支持新字段

### Phase 4：输出 + 知识库集成（30min）
- [x] 4.1 增强 markdown_gen.py：推荐理由、购买链接提示
- [x] 4.2 知识库索引自动生成（__索引.md）
- [x] 4.3 统计.md 自动更新

---

## 九、依赖变更

```diff
# requirements.txt
- httpx>=0.25.0
- beautifulsoup4>=4.12.0
  playwright>=1.40.0
  pytest>=7.0.0
+ click>=8.0
+ pyyaml>=6.0
+ rich>=13.0
```

移除未使用的 httpx 和 beautifulsoup4，新增 click（CLI）、pyyaml（YAML frontmatter）、rich（终端表格显示）。

---

## 十、非目标（Scoped Out）

- ❌ Web 界面（用户明确不要）
- ❌ 多数据源（Future：亚马逊/当当/京东）
- ❌ AI 生成推荐语（Future：考虑集成 LLM 写推荐摘要）
- ❌ Docker/部署（本地工具）
