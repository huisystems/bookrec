# bookrec

自动化书籍推荐工具。从豆瓣抓取经管与 AI 类优质图书，经筛选和排序后沉淀为可浏览的 Obsidian 知识库。

---

## 功能特性

- **豆瓣数据抓取** — 自动爬取豆瓣最新上架和标签页面的经管、AI 类图书，跨分类自动去重
- **智能筛选与排序** — 支持按评分、评价人数、出版日期多条件过滤；采用加权评分（综合评分、人气、时效性）进行排序
- **Obsidian 知识库** — 每本书保存为独立的 Markdown 文件，包含 YAML 元数据，按分类组织目录；自动生成索引和统计
- **双语命令行界面** — 基于 Click 构建，中文描述配合英文兼容的选项名称；Rich 格式表格输出
- **全文搜索** — 支持按书名、作者、简介进行全文检索
- **推荐导出** — 支持将推荐列表导出为 Markdown 文件或 JSON 格式
- **笔记功能** — 为任意图书添加个人笔记，持久化存储于知识库中

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 从豆瓣抓取最新图书
bookrec fetch

# 生成推荐排行列表
bookrec recommend --top 10 --output 推荐.md
```

---

## 安装指南

### 环境要求

- **Python 3.10** 或更高版本
- **Playwright**（使用 `playwright install chromium` 自动下载）

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/your-username/bookrec.git
cd bookrec

# 创建并激活虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows 系统: .venv\Scripts\activate

# 安装依赖包
pip install -r requirements.txt

# 安装 Playwright Chromium 浏览器
playwright install chromium
```

### 开发模式安装

```bash
pip install -e .
```

安装完成后，`bookrec` 命令即可在终端中使用。你也可以通过以下方式运行：

```bash
python -m src.cli.app
# 或
python main.py
```

---

## 使用指南

### 从豆瓣抓取图书

```bash
# 抓取近 12 个月的经管和 AI 类图书（默认）
bookrec fetch

# 指定分类和时间范围
bookrec fetch --category 经管,AI --months 12

# 增加每标签抓取页数以获取更多数据
bookrec fetch --category AI --months 6 --max-pages 5

# 仅抓取基础信息，跳过简介和目录
bookrec fetch --no-detail
```

**参数说明：**

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `-c, --category` | `经管,AI` | 分类，多个用逗号分隔 |
| `-m, --months` | `12` | 抓取近 N 个月出版的图书 |
| `--max-pages` | `2` | 每个标签最多抓取页数 |
| `--no-detail` | `false` | 不获取详情（简介和目录） |

### 生成推荐列表

```bash
# 全分类 Top 10 推荐（默认）
bookrec recommend

# 经管类 Top 20，评分不低于 8.0
bookrec recommend --top 20 --category 经管 --min-rating 8.0

# 导出为 Markdown 文件
bookrec recommend --top 10 --output 推荐.md

# 导出为 JSON
bookrec recommend --json
```

**参数说明：**

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `-n, --top` | `10` | 推荐数量 |
| `-c, --category` | 全部 | 限定分类（`经管` 或 `AI`） |
| `--min-rating` | `7.0` | 最低评分 |
| `--min-rating-count` | `20` | 最低评价人数 |
| `-o, --output` | 终端输出 | 输出到 Markdown 文件 |
| `--json` | `false` | 输出为 JSON 格式 |

### 浏览知识库

```bash
# 列出知识库中的所有图书
bookrec list-books

# 按分类筛选
bookrec list-books --category 经管

# 按最低评分筛选
bookrec list-books --min-rating 8

# 按标签筛选
bookrec list-books --tag 机器学习
```

**参数说明：**

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `-c, --category` | 全部 | 限定分类 |
| `--min-rating` | `0` | 最低评分 |
| `--tag` | 全部 | 按标签筛选 |

### 搜索图书

```bash
# 全文搜索书名、作者和简介
bookrec search 深度学习
bookrec search "Seymour Papert"
```

### 添加笔记

```bash
bookrec note <豆瓣ID> 你的笔记内容
```

每次执行会覆盖该图书已有的笔记。笔记以 YAML 元数据形式存储在图书文件中。

### 查看知识库统计

```bash
bookrec stats
```

显示图书总数、按分类的分布柱状图以及知识库路径。

### 查看推荐历史

```bash
bookrec history
```

列出知识库 `推荐列表/` 目录中所有已生成的推荐文件。

### 全局选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--vault` | `./知识库/` | Obsidian 知识库路径（也可通过 `BOOKREC_VAULT` 环境变量设置） |
| `--verbose` | `false` | 显示调试日志 |
| `--help` | | 显示帮助信息 |

---

## 配置说明

配置文件位于 `src/core/config.py`。主要默认值：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `FETCH_MONTHS` | `12` | 默认抓取回溯月数 |
| `DEFAULT_TOP_N` | `10` | 默认推荐数量 |
| `DEFAULT_MIN_RATING` | `7.0` | 默认最低评分 |
| `DEFAULT_MIN_RATING_COUNT` | `20` | 默认最低评价人数 |
| `VAULT_PATH` | `./知识库/` | 默认知识库路径 |

### 环境变量

| 变量 | 说明 |
|------|------|
| `BOOKREC_VAULT` | 覆盖默认的知识库路径 |

示例：

```bash
export BOOKREC_VAULT=/path/to/my/obsidian/vault
bookrec fetch
```

---

## 项目结构

```
bookrec/
├── main.py                  # 快速启动入口
├── pyproject.toml           # 包元数据与构建配置
├── requirements.txt         # 依赖列表
├── CONTRIBUTING.md          # 贡献指南
├── README.md                # 英文文档
├── README.zh-CN.md          # 中文文档
│
├── src/
│   ├── cli/
│   │   └── app.py           # Click CLI：7 个命令
│   ├── core/
│   │   └── config.py        # 全局配置
│   ├── data_sources/
│   │   ├── base.py          # 数据源抽象接口
│   │   └── douban.py        # 豆瓣爬虫（基于 Playwright）
│   ├── knowledge/
│   │   └── store.py         # Obsidian 知识库存储层
│   ├── models/
│   │   └── book.py          # 图书数据模型（dataclass）
│   ├── output/
│   │   └── markdown_gen.py  # Markdown 生成与评分星级
│   └── services/
│       ├── orchestrator.py  # 核心编排逻辑
│       └── filter.py        # 筛选与排序引擎
│
├── tests/
│   ├── test_book_model.py
│   ├── test_douban_category.py
│   ├── test_filter.py
│   ├── test_markdown_gen.py
│   └── test_store.py
│
└── 知识库/                    # 默认 Obsidian 知识库（git 忽略）
    ├── 图书/                  # 按分类存放的图书条目
    ├── 推荐列表/              # 生成的推荐文件
    ├── 数据源快照/            # 原始数据快照
    └── 统计.md               # 自动更新的知识库统计
```

---

## 数据处理流程

```
豆瓣 (Douban)
    │
    ▼
  fetch ──── Playwright 抓取最新上架与标签页面
    │
    ▼
  dedup ──── 按 douban_id 合并，跳过重复
    │
    ▼
  detail ──── 补充简介和目录信息
    │
    ▼
  store ──── 保存为 YAML 元数据的 Markdown 文件至 Obsidian 知识库
    │
    ▼
  filter ──── 按评分、评价人数、出版日期过滤
    │
    ▼
  rank ────── 加权评分 = 评分 × 0.5 + log(评价人数) × 0.3 + 时效性 × 0.2
    │
    ▼
recommend ── 输出排序列表至 Markdown、JSON 或终端表格
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | **Python 3.14+**（需 >= 3.10） |
| CLI 框架 | **Click** 8.x |
| 浏览器自动化 | **Playwright** 1.40+ |
| 数据序列化 | **PyYAML** 6.x |
| 终端界面 | **Rich** 13+ |
| 测试框架 | **Pytest** 7+（超过 44 项测试） |
| 存储格式 | **Obsidian 兼容 Markdown**，附 YAML 元数据 |

---

## 参与贡献

欢迎贡献代码！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解完整的贡献指南，包括：

- 开发环境搭建与安装
- 编码规范（PEP 8、类型注解、命名约定）
- Conventional Commits 提交格式
- 拉取请求流程与问题报告

---

## 许可证

本项目采用 **Apache License 2.0** 授权。详见 [LICENSE](LICENSE) 文件。
