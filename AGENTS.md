# AGENTS.md — Agent 工作守则

> **适用范围**：本仓库 (huisystems/bookrec) 所有 AI Agent / 开发者
> **生效日期**：2026-07-01
> **配套文档**：`/Users/titan/projects-2026/06月17日及以后/063001-分支规划与生产环境安全问题/Git分支管理细则-Agent实施指引.md`

---

## 1. Git Flow 分支体系（强制执行）

### 1.1 分支结构

| 分支 | 来源 | 合并目标 | 环境映射 | 保护级别 |
|------|------|----------|----------|----------|
| `main` | — | — | 生产 (hui2/hui3) | ≥2 人审批 |
| `develop` | main | — | 测试 (hui1) | ≥1 人审批 |
| `feature/*` | develop | develop | 开发 (hui5) | 自行管理 |
| `bugfix/*` | develop | develop | 开发 (hui5) | 自行管理 |
| `release/*` | develop | main + develop | 预发布 (hui1) | ≥1 人审批 |
| `hotfix/*` | main | main + develop | 生产 (hui2/hui3) | ≥2 人审批 |

### 1.2 五条铁律（绝对禁止违反）

1. **main 永远只接收 release/* 和 hotfix/* 的合并，绝不接收 feature/* 直合并**
2. **禁止任何形式的 git push --force 到 main 和 develop 分支**
3. **临时分支（feature/bugfix/release/hotfix）合并后必须立即删除**
4. **一个分支只做一件事——一个 feature、一个 bugfix、一个 release、一个 hotfix**
5. **main 上的每个提交都必须是可部署状态，绝不提交半成品代码**

### 1.3 命名规范

- 全小写英文，单词用连字符 `-` 分隔
- 仅允许 `a-z`、`0-9`、`-`
- 不超过 40 字符
- `release/` 必须用版本号 `vX.Y.Z`
- 描述性命名，禁止 `tmp`/`test`/`wip`/`123` 等

### 1.4 合并策略

| 操作 | 策略 | 命令 |
|------|------|------|
| feature → develop | `--no-ff` | `git merge --no-ff feature/xxx` |
| release → main | `--no-ff` | PR merge |
| hotfix → main | `--no-ff` | PR merge |
| release/hotfix → develop | `--no-ff` | PR merge |

### 1.5 Commit 规范

格式：`<类型>(<范围>): <简短描述>`

类型：`feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `chore` / `ci` / `build` / `revert`

规则：一个 commit 只做一件事；描述用祈使句；不超过 50 字符；末尾不加句号。

---

## 2. 仓库专属信息

### 2.1 远程配置
- **URL**: `git@github.com:huisystems/bookrec.git`（SSH，非 HTTPS）
- **Owner**: huisystems
- **当前分支状态**: main + develop（HEAD f71a6e0）+ tag v0.2.3

### 2.2 SSH 注意事项（重要）
仓库 `origin` 必须保持 SSH URL。**禁止**重新加上全局 `url.https://github.com/.insteadof=git@github.com:` 重写规则（这会导致 SSH → HTTPS 重写，使 push 失败需要输入密码）。

### 2.3 环境配置
- **Python**: 已配置 `.venv`，使用 `uv` 管理（项目用 ruff + pytest）
- **CI**: GitHub Actions（见 `.github/workflows/`）
- **Python 版本**: 3.12

---

## 3. 标准工作流

### 3.1 开发新功能
```bash
./scripts/git-flow/new-feature.sh <功能名>
# 编写代码 + 提交
gh pr create --base develop --head feature/<功能名>
# PR 合并后
./scripts/git-flow/merge-feature.sh feature/<功能名>
```

### 3.2 修复非紧急 bug
```bash
./scripts/git-flow/new-feature.sh fix-<问题描述>
# （或 ./scripts/git-flow/bugfix.sh 待加）
# 同 feature 流程
```

### 3.3 准备发布
```bash
./scripts/git-flow/new-release.sh X.Y.Z
# 在 release/vX.Y.Z 上只修 bug
gh pr create --base main --head release/vX.Y.Z
gh pr create --base develop --head release/vX.Y.Z
# main 合并后
git tag -a vX.Y.Z -m "发布 vX.Y.Z"
git push origin vX.Y.Z
```

### 3.4 紧急修复生产
```bash
./scripts/git-flow/new-hotfix.sh <修复描述>
gh pr create --base main --head hotfix/<描述>      # 加急审批
gh pr create --base develop --head hotfix/<描述>   # 同步修复
# main 合并后，修订号 +1 打 tag
```

---

## 4. Agent 行为准则

### 4.1 操作前必读
- 任何 Git 操作前：先 `git status`、`git branch --show-current`
- 创建新分支前：先 `git fetch origin` + 切到源分支 + `git pull`
- 提交前：检查是否在正确分支上（不要在 main 直接改）

### 4.2 禁止行为
- ❌ force push 到 main / develop / release/* / hotfix/*
- ❌ 直接 push 到 main / develop（必须走 PR）
- ❌ feature 直接合并到 main
- ❌ 在 release 分支添加新功能
- ❌ 在 hotfix 添加无关变更
- ❌ commit 敏感信息（密钥、token、cookie）
- ❌ 删除 main 或 develop 分支
- ❌ 一个分支做多件不相关的事
- ❌ 不删除已合并的临时分支
- ❌ 切换远程 URL 回 HTTPS

### 4.3 Tag 与版本
- Tag 仅在 release 或 hotfix 合并到 main 后打
- 格式：`vX.Y.Z`（语义化版本）
- 附注标签（`-a`）而非轻量标签

---

## 5. 验证检查清单

每次涉及 Git 操作时确认：
- [ ] 分支名符合命名规范
- [ ] 当前在正确的源分支上
- [ ] 没有未提交的工作
- [ ] 远程跟踪关系正确
- [ ] merge 使用 `--no-ff`
- [ ] 临时分支合并后已删除

---

## 6. 参考文档

- **完整规范**: `/Users/titan/projects-2026/06月17日及以后/063001-分支规划与生产环境安全问题/Git分支管理细则-Agent实施指引.md`
- **总纲**: `/Users/titan/projects-2026/06月17日及以后/063001-分支规划与生产环境安全问题/分支规划与生产环境安全策略.md`
- **自动化脚本**: `scripts/git-flow/`
- **分支保护配置**: `./scripts/git-flow/setup-branch-protection.sh`

---

> **重要**：未来任何 agent 进入此仓库工作前，请先读本文档。任何违反铁律的操作将视为事故处理。
