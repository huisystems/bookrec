#!/usr/bin/env bash
# ============================================================
# scripts/git-flow/new-release.sh
# 从 develop 创建 release 分支
# 用法: ./scripts/git-flow/new-release.sh <版本号>
# 示例: ./scripts/git-flow/new-release.sh 1.2.0
# ============================================================

set -euo pipefail

VERSION="${1:-}"

if [[ -z "${VERSION}" ]]; then
  cat <<EOF
用法: $0 <版本号>
示例: $0 1.2.0

版本号格式: X.Y.Z (语义化版本)
  - 主版本 X+1: 不兼容的重大变更
  - 次版本 Y+1: 向后兼容的新功能
  - 修订号 Z+1: 向后兼容的 bug 修复 (hotfix)
EOF
  exit 1
fi

# 验证版本号格式
if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
  echo "错误: 版本号格式应为 X.Y.Z，例如 1.2.0"
  echo "      当前输入: ${VERSION}"
  exit 1
fi

BRANCH="release/v${VERSION}"
TAG="v${VERSION}"

# release 从 develop 创建
echo ">> 切到 develop 并拉取最新..."
git checkout develop
git pull --rebase=false origin develop

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "错误: 本地分支 ${BRANCH} 已存在"
  exit 1
fi

if git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
  echo "错误: 远程分支 origin/${BRANCH} 已存在"
  exit 1
fi

# 检查 tag 是否已存在
if git tag -l "${TAG}" | grep -q "^${TAG}$"; then
  echo "错误: tag ${TAG} 已存在"
  exit 1
fi

git checkout -b "${BRANCH}"
git push -u origin "${BRANCH}"

cat <<EOF

✓ release 分支已创建: ${BRANCH}
⚠ 在 release 分支上只允许修复 bug，不要添加新功能

下一步（验收通过后必须创建两个 PR，先合 main 再合 develop）:

  # PR1: release → main
  gh pr create --base main --head ${BRANCH} \\
    --title "release: ${TAG}" \\
    --body "## 发布内容\n- 功能 A\n- 功能 B\n- 修复 C\n\n## 验收情况\n- [ ] 预发布环境 UAT 通过\n- [ ] QA 测试通过\n\n## 审批\n- [ ] ≥2 人审批"

  # PR2: release → develop (同步 release 期间的修复)
  gh pr create --base develop --head ${BRANCH} \\
    --title "release: ${TAG} 同步到 develop"

  # main 合并后打 tag
  git checkout main && git pull origin main
  git tag -a ${TAG} -m "发布 ${TAG}

新增功能:
- ...

修复:
- ...

已知问题:
- ..."
  git push origin ${TAG}
EOF
