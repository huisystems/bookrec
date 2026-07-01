#!/usr/bin/env bash
# ============================================================
# scripts/git-flow/setup-branch-protection.sh
# 配置 GitHub 仓库的分支保护规则
#
# 前置条件:
#   1. 已安装 gh CLI: brew install gh
#   2. 已登录仓库所在组织: gh auth login
#   3. 当前账号是该仓库的 admin/maintain
#
# 用法: ./scripts/git-flow/setup-branch-protection.sh
#
# 说明:
#   本脚本通过 GitHub REST API 配置 main / develop / release/* / hotfix/*
#   的分支保护规则，符合《Git 分支管理细则》第八章要求。
# ============================================================

set -euo pipefail

REPO="${REPO:-huisystems/bookrec}"

echo "=========================================="
echo " 配置 ${REPO} 的 GitHub 分支保护"
echo "=========================================="
echo ""

# 前置检查
if ! command -v gh >/dev/null 2>&1; then
  echo "错误: 未找到 gh CLI，请先安装: brew install gh"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "错误: gh CLI 未登录，请先执行: gh auth login"
  exit 1
fi

echo "当前 gh 身份:"
gh auth status 2>&1 | head -5
echo ""

# 确认仓库存在
if ! gh repo view "${REPO}" >/dev/null 2>&1; then
  echo "错误: 仓库 ${REPO} 不存在或无访问权限"
  exit 1
fi

echo "目标仓库: ${REPO}"
echo ""

# 配置 main 分支保护（≥2 人审批，禁止 force push）
echo "[1/4] 配置 main 分支保护（≥2 人审批）..."
gh api "repos/${REPO}/branches/main/protection" \
  --method PUT \
  --input - <<'JSON' | head -5
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": true,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
JSON
echo "  ✓ main 已配置"

# 配置 develop 分支保护（≥1 人审批）
echo ""
echo "[2/4] 配置 develop 分支保护（≥1 人审批）..."
gh api "repos/${REPO}/branches/develop/protection" \
  --method PUT \
  --input - <<'JSON' | head -5
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": true,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
JSON
echo "  ✓ develop 已配置"

# 配置 release/* 分支保护
echo ""
echo "[3/4] 配置 release/* 分支保护（≥1 人审批）..."
gh api "repos/${REPO}/branches/release%2A/protection" \
  --method PUT \
  --input - <<'JSON' | head -5
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
echo "  ✓ release/* 已配置"

# 配置 hotfix/* 分支保护
echo ""
echo "[4/4] 配置 hotfix/* 分支保护（≥2 人审批，紧急时可临时调整）..."
gh api "repos/${REPO}/branches/hotfix%2A/protection" \
  --method PUT \
  --input - <<'JSON' | head -5
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true
  },
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
echo "  ✓ hotfix/* 已配置"

echo ""
echo "=========================================="
echo " ✓ 分支保护规则配置完成"
echo "=========================================="
echo ""
echo "验证方式:"
echo "  gh api repos/${REPO}/branches/main/protection | head -20"
echo "  gh api repos/${REPO}/branches/develop/protection | head -20"
echo ""
echo "如需调整审批人数或添加必需的 CI 检查，请:"
echo "  1. 编辑本脚本中的 required_approving_review_count 和 contexts"
echo "  2. 重新运行"
