#!/usr/bin/env bash
# ============================================================
# scripts/git-flow/cleanup-branches.sh
# 批量清理已合并到 develop 的 feature/bugfix 分支
# 用法: ./scripts/git-flow/cleanup-branches.sh [--force]
# ============================================================

set -euo pipefail

FORCE="false"
if [[ "${1:-}" == "--force" ]]; then
  FORCE="true"
fi

echo "=========================================="
echo " 已合并到 develop 的临时分支"
echo "=========================================="

# 列出已合并的 feature/bugfix 分支
MERGED=$(git branch --merged develop | grep -E '^\s+(feature|bugfix)/' | sed 's/^\s*//' | sed 's/remotes\/origin\///g' | sort -u)

if [[ -z "${MERGED}" ]]; then
  echo "没有已合并但未删除的 feature/bugfix 分支，仓库很整洁！"
  exit 0
fi

echo "${MERGED}"
echo ""

if [[ "${FORCE}" != "true" ]]; then
  echo "是否删除以上分支？(y/N)"
  read -r CONFIRM

  if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    echo "已取消"
    exit 0
  fi
fi

echo "${MERGED}" | while read -r branch; do
  # 跳过 origin/ 前缀的远程分支
  clean_branch="${branch#origin/}"

  if git show-ref --verify --quiet "refs/heads/${clean_branch}"; then
    git branch -d "${clean_branch}" && echo "✓ 已删除本地: ${clean_branch}"
  fi

  if git ls-remote --exit-code --heads origin "${clean_branch}" >/dev/null 2>&1; then
    git push origin --delete "${clean_branch}" 2>/dev/null && echo "✓ 已删除远程: ${clean_branch}" || true
  fi
done

echo ""
echo "清理完成！"
