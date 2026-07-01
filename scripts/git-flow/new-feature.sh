#!/usr/bin/env bash
# ============================================================
# scripts/git-flow/new-feature.sh
# 从 develop 创建 feature 分支
# 用法: ./scripts/git-flow/new-feature.sh <功能名>
# 示例: ./scripts/git-flow/new-feature.sh user-registration
# ============================================================

set -euo pipefail

FEATURE_NAME="${1:-}"

if [[ -z "${FEATURE_NAME}" ]]; then
  cat <<EOF
用法: $0 <功能名>
示例: $0 user-registration

命名规范:
  - 全小写英文，单词用连字符分隔
  - 不超过 40 字符
  - 描述性，禁止 tmp/test/wip 等
EOF
  exit 1
fi

BRANCH="feature/${FEATURE_NAME}"

# 校验命名
if [[ ! "${FEATURE_NAME}" =~ ^[a-z0-9][a-z0-9-]{0,38}[a-z0-9]$ ]]; then
  echo "错误: 功能名必须全小写字母/数字/连字符，且不能以连字符开头/结尾"
  echo "      当前输入: ${FEATURE_NAME}"
  exit 1
fi

# 确保在 develop 最新代码上创建
echo ">> 切到 develop 并拉取最新..."
git checkout develop
git pull --rebase=false origin develop

# 检查分支是否已存在
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "错误: 本地分支 ${BRANCH} 已存在"
  exit 1
fi

if git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
  echo "错误: 远程分支 origin/${BRANCH} 已存在"
  exit 1
fi

# 创建并推送
git checkout -b "${BRANCH}"
git push -u origin "${BRANCH}"

cat <<EOF

✓ feature 分支已创建: ${BRANCH}
✓ 已推送到远程仓库

下一步:
  # 开发完成后创建 PR
  gh pr create --base develop --head ${BRANCH} \\
    --title "feat: ${FEATURE_NAME}" \\
    --body "## 变更内容\n- ...\n\n## 测试情况\n- [ ] 本地单测通过\n- [ ] 开发环境验证通过\n- [ ] CI 自动测试通过"
EOF
