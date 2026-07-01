#!/usr/bin/env bash
# ============================================================
# scripts/git-flow/new-hotfix.sh
# 从 main 创建 hotfix 分支（紧急修复用）
# 用法: ./scripts/git-flow/new-hotfix.sh <修复描述>
# 示例: ./scripts/git-flow/new-hotfix.sh security-patch-sql-injection
# ============================================================

set -euo pipefail

HOTFIX_NAME="${1:-}"

if [[ -z "${HOTFIX_NAME}" ]]; then
  cat <<EOF
用法: $0 <修复描述>
示例: $0 security-patch-sql-injection

注意: hotfix 必须从 main 创建，仅用于生产环境紧急修复
EOF
  exit 1
fi

BRANCH="hotfix/${HOTFIX_NAME}"

# 校验命名
if [[ ! "${HOTFIX_NAME}" =~ ^[a-z0-9][a-z0-9-]{0,38}[a-z0-9]$ ]]; then
  echo "错误: 修复描述必须全小写字母/数字/连字符"
  echo "      当前输入: ${HOTFIX_NAME}"
  exit 1
fi

# hotfix 必须从 main 创建
echo ">> 切到 main 并拉取最新（hotfix 必须从 main 拉出）..."
git checkout main
git pull --rebase=false origin main

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "错误: 本地分支 ${BRANCH} 已存在"
  exit 1
fi

if git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
  echo "错误: 远程分支 origin/${BRANCH} 已存在"
  exit 1
fi

git checkout -b "${BRANCH}"
git push -u origin "${BRANCH}"

cat <<EOF

✓ hotfix 分支已创建: ${BRANCH}
⚠ 紧急修复，请保持最小化变更——只修 bug，不加任何功能！

下一步（修复完成后必须创建两个 PR，先合 main 再合 develop）:

  # PR1: hotfix → main
  gh pr create --base main --head ${BRANCH} \\
    --title "hotfix: ${HOTFIX_NAME}" \\
    --body "## 紧急修复\n- ...\n\n## 影响范围\n- ...\n\n## 审批\n- [ ] 技术负责人审批（加急）"

  # PR2: hotfix → develop (同步修复)
  gh pr create --base develop --head ${BRANCH} \\
    --title "hotfix: 同步 ${HOTFIX_NAME} 修复到 develop"

  # main 合并后打 tag（修订号 +1）
  # 例如上一个版本是 v1.2.0，则 hotfix 版本为 v1.2.1
  git checkout main && git pull origin main
  git tag -a vX.Y.Z -m "hotfix: ${HOTFIX_NAME}"
  git push origin vX.Y.Z
EOF
