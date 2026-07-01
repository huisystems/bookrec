# Git Flow 自动化脚本

> 本目录包含基于《Git 分支管理细则 — Agent 实施指引》第十三章的自动化脚本。

## 脚本清单

| 脚本 | 用途 | 用法 |
|------|------|------|
| `new-feature.sh` | 从 develop 创建 feature 分支 | `./scripts/git-flow/new-feature.sh <功能名>` |
| `new-hotfix.sh` | 从 main 创建 hotfix 分支 | `./scripts/git-flow/new-hotfix.sh <修复描述>` |
| `new-release.sh` | 从 develop 创建 release 分支 | `./scripts/git-flow/new-release.sh <版本号>` |
| `merge-feature.sh` | 合并 feature/bugfix 到 develop 并清理 | `./scripts/git-flow/merge-feature.sh <分支名>` |
| `cleanup-branches.sh` | 批量清理已合并分支 | `./scripts/git-flow/cleanup-branches.sh [--force]` |
| `setup-branch-protection.sh` | 配置 GitHub 分支保护规则 | `./scripts/git-flow/setup-branch-protection.sh` |

## 快速开始

```bash
# 1. 赋予执行权限（一次性）
chmod +x scripts/git-flow/*.sh

# 2. 创建 feature 分支
./scripts/git-flow/new-feature.sh my-awesome-feature

# 3. 开发完成后合并并清理
./scripts/git-flow/merge-feature.sh feature/my-awesome-feature

# 4. 定期清理已合并的临时分支
./scripts/git-flow/cleanup-branches.sh
```

## 分支保护配置

`setup-branch-protection.sh` 需要：

1. 已安装 gh CLI（`brew install gh`）
2. 已登录（`gh auth login`）
3. 当前账号是该仓库的 admin/maintain

配置完成后将启用：

| 分支模式 | 审批人数 | force push | 直接 push |
|----------|----------|-----------|----------|
| `main` | ≥2 | 禁止 | 禁止 |
| `develop` | ≥1 | 禁止 | 禁止 |
| `release/*` | ≥1 | 禁止 | 禁止 |
| `hotfix/*` | ≥2 | 禁止 | 禁止 |

## 命名规范提醒

- 全小写英文，单词用连字符分隔
- 仅允许 `a-z`、`0-9`、`-`
- 名称描述功能/问题，禁止 `tmp`/`test`/`wip`
- `release/` 必须用版本号 `vX.Y.Z`
- 长度不超过 40 字符
