# 发布运行手册

本项目用 GitHub Actions + OIDC trusted publishing 自动发布到 PyPI。
本手册说明：从本地打 tag，到 PyPI 上能 `pip install bookrec` 的完整流程。

---

## 发布流程总览

```
本地打 tag → push tag → CI 自动 build + 推 TestPyPI
                                  ↓
                    维护者手动跑 workflow_dispatch 选 pypi
                                  ↓
                              CI 推 PyPI
                                  ↓
                  GitHub → Releases → Draft release
                                  ↓
                    用户可以 `pip install bookrec==0.2.x`
```

---

## Step 0 — 前置一次性配置（只做一次）

### 0.1 PyPI 账号

- 注册 https://pypi.org/ 账号（启用 2FA）
- 同样的流程在 https://test.pypi.org/ 注册（独立账号/项目）

### 0.2 在 PyPI 创建项目

- 首次发布前，先在 https://pypi.org/manage/projects/ 手动创建 `bookrec` 项目
- 填入：name、description、author 等基本信息
- 后续版本都通过 trusted publishing 推送

### 0.3 配置 trusted publishing（PyPI 端）

在 https://pypi.org/manage/account/publishing/ 添加 trusted publisher：

| 字段 | 值 |
|---|---|
| Owner | `huisystems` |
| Repository name | `bookrec` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

在 https://test.pypi.org/manage/account/publishing/ 同样配置一遍（environment name 用 `testpypi`）。

### 0.4 GitHub 端配置 Environment

- 仓库 → Settings → Environments
- 创建 `pypi` environment：可加 required reviewers（手动批准）
- 创建 `testpypi` environment：通常不设审批（自动跑）

---

## Step 1 — 本地准备

### 1.1 收口 CHANGELOG

将 `## [Unreleased]` 段重命名为 `## [X.Y.Z] - YYYY-MM-DD`，并把日期改成今天。

### 1.2 Bump 版本

编辑 `pyproject.toml`：

```toml
[project]
name = "bookrec"
version = "X.Y.Z"
```

### 1.3 本地最终验证

按 publish workflow 在 CI 跑的顺序全跑一遍：

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
rm -rf dist/ build/
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*

# 干净 venv 试装
python3 -m venv /tmp/test-venv
/tmp/test-venv/bin/pip install dist/bookrec-*.whl
/tmp/test-venv/bin/bookrec --help
rm -rf /tmp/test-venv dist/ build/
```

**真实豆瓣抓取冒烟**（推荐，每次发版前跑一次）：

```bash
.venv/bin/python smoke_fetch.py
```

脚本会创建临时 vault，真实调一次 `bookrec fetch --category AI --max-pages 1`，验证：
- CLI exit 0
- 至少抓回 1 本
- 书文件 YAML frontmatter 完整
- detail fetch 触发的 `## 简介` section 生成

需要 `playwright install chromium`（首次）。脚本不会写数据到项目 `知识库/`，只用 tmp 目录。

全部应通过。

### 1.4 Commit + Tag

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): bump to X.Y.Z and convert Unreleased to X.Y.Z"

git tag -a vX.Y.Z -m "vX.Y.Z — <one-line summary>"
```

---

## Step 2 — Push（需要 GitHub 凭据）

```bash
git push origin main --tags
```

如果 `git push` 报 `could not read Username`，需要先配凭据：

```bash
# 选项 A: 配环境变量 (PAT)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
git push https://x-access-token:$GITHUB_TOKEN@github.com/huisystems/bookrec.git main --tags

# 选项 B: 用 SSH
git remote set-url origin git@github.com:huisystems/bookrec.git
ssh-add ~/.ssh/id_ed25519
git push origin main --tags

# 选项 C: 用 GitHub CLI
gh auth login
git push origin main --tags
```

---

## Step 3 — Tag 推送后自动发生的事

`vX.Y.Z` tag push 触发 `.github/workflows/publish.yml`：

1. **build job**：
   - 跑 tests
   - 跑 ruff check / format check
   - build sdist + wheel
   - `twine check` 验证 metadata
   - upload `dist/` artifact

2. **publish job**（仅 tag push / manual）：
   - download artifact
   - **推 TestPyPI**（tag push 时默认）
   - 修在 PyPI 项目的 trusted publisher 后即生效

观察：
- 仓库 → Actions → 选 "Publish" workflow
- 应该看到 green checkmark
- TestPyPI 端：https://test.pypi.org/project/bookrec/ 能看到 vX.Y.Z

---

## Step 4 — 手动发布到正式 PyPI

⚠️ 这步**必须**手动——tag push 只试发 TestPyPI，PyPI 需要维护者显式确认：

1. 仓库 → Actions → "Publish" workflow
2. 右上角 "Run workflow" → Branch: main → Target: `pypi` → 绿色 "Run workflow" 按钮
3. 等待 green
4. PyPI 端验证：https://pypi.org/project/bookrec/ 能看到 vX.Y.Z

---

## Step 5 — GitHub Release

⚠️ 这一步**不**自动（避免 OIDC publishing 与 GitHub Release 之间的隐式耦合）：

1. 仓库 → Releases → "Draft a new release"
2. Choose tag: `vX.Y.Z`
3. Release title: `vX.Y.Z`
4. Description: 粘贴 `CHANGELOG.md` 中对应版本段，扩充 TL;DR / install 命令
5. Publish release

---

## Step 6 — 验证

```bash
# 在干净 venv 中
python3 -m venv /tmp/verify
/tmp/verify/bin/pip install bookrec==X.Y.Z
/tmp/verify/bin/bookrec --help
/tmp/verify/bin/bookrec stats
rm -rf /tmp/verify
```

应正常显示版本号和命令帮助。

---

## 故障排查

| 症状 | 原因 | 修法 |
|---|---|---|
| `twine check` 报 `long_description` missing | `pyproject.toml` 缺 `readme` 字段 | 添加 `readme = "README.md"` |
| workflow 报 `OIDC: failed to exchange token` | PyPI 端 trusted publisher 配置错 | 检查 owner / repo / workflow filename / environment name 四项完全一致 |
| workflow 报 `403: project not found` | PyPI 上还没手动创建项目 | https://pypi.org/manage/projects/ 手动创建 |
| `pip install` 后 `bookrec: command not found` | `pyproject.toml [project.scripts]` 配错 | 检查 `bookrec = "src.cli.app:main"` |
| 推到 PyPI 后 metadata 显示 "UNKNOWN" | `pyproject.toml` 缺 `author` / `license` 等 | 补全 classifiers 与 author 字段 |
| vX.Y.Z 推过一次后改不重推 | PyPI 拒绝覆盖已发布版本 | bump 到 vX.Y.Z+1（PyPI 不允许重发同版本） |
