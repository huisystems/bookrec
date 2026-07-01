#!/usr/bin/env bash
# ============================================================
# scripts/git-flow/merge-feature.sh
# 合并 feature/bugfix 分支到 develop（--no-ff 保留历史）并清理
# 用法: ./scripts/git-flow/merge-feature.sh <feature/bugfix 分支名>
# 示例: ./scripts/git-flow/merge-feature.sh feature/user-registration
# ============================================================

set -euo pipefail

BRANCH="${1:-}"

if [[ -z "${BRANCH}" ]]; then
  cat <<EOF
用法: $0 <分支名>
示例: $0 feature/user-registration

注意: 此脚本仅用于合并到 develop 的临时分支（feature/bugfix）
      release/hotfix 分支请使用专用合并流程（需打 tag）
EOF
  exit 1
fi

if [[ ! "${BRANCH}" =~ ^(feature|bugfix)/ ]]; then
  echo "错误: 分支名必须以 feature/ 或 bugfix/ 开头"
  echo "      当前输入: ${BRANCH}"
  exit 1
fi

# 切到 develop 并拉取最新
echo ">> 切到 develop 并拉取最新..."
git checkout develop
git pull --rebase=false origin develop

# 确认源分支存在
if ! git show-ref --verify --quiet "refs/heads/${BRANCH}" && \
   ! git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
  echo "错误: 分支 ${BRANCH} 在本地和远程都不存在"
  exit 1
fi

# 确保有最新源分支
echo ">> 拉取 ${BRANCH} 最新代码..."
if git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
  git fetch origin "${BRANCH}"
fi

# 合并（--no-ff 保留分支历史）
echo ">> 合并 ${BRANCH} 到 develop（使用 --no-ff 保留历史）..."
git merge --no-ff "${BRANCH}" -m "merge: ${BRANCH} into develop"

# 推送 develop
echo ">> 推送 develop 到远程..."
git push origin develop

# 删除分支
echo ">> 清理分支..."
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git branch -d "${BRANCH}"
fi

if git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
  git push origin --delete "${BRANCH}"
fi

cat <<EOF

✓ ${BRANCH} 已合并到 develop
✓ develop 已推送到远程
✓ ${BRANCH} 已删除（本地+远程）

验证:
  git log --oneline --graph --decorate -5
EOF
