# 把本地 commits 推到 origin（不带 tag）

## 一次性环境配置

如果你还没配 GitHub 凭据，从下面选一种：

### 方式 A: GitHub CLI（最方便）
```bash
gh auth login
# 跟着交互走：HTTPS recommended, paste auth token
```

### 方式 B: Personal Access Token
```bash
# 在 https://github.com/settings/tokens 生成一个 token (classic, 'repo' scope)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# 把 remote 改成可注入 token 的形式
git remote set-url origin https://x-access-token:${GITHUB_TOKEN}@github.com/huisystems/bookrec.git
```

### 方式 C: SSH
```bash
git remote set-url origin git@github.com:huisystems/bookrec.git
ssh-add ~/.ssh/id_ed25519  # 或你的 key
```

## 推 commits（不推 tag）

⚠️ **关键**：先只推 commits。`v0.2.2` tag **不**推——反爬修复前发到 PyPI 会给用户 0 本空抓取。

```bash
cd /Users/titan/projects-2026/projectsQ2/18-书籍书目推荐自动化-github-pub
git push origin main
```

如果你想连同 tag 一起推（不推荐）：
```bash
git push origin main --tags  # ⚠️ 会推 v0.2.2 → 触发 publish workflow
```

## 推完后验证

```bash
# 远端应该看到 24 个新 commit
git log --oneline origin/main..HEAD  # 应为空（推完后）

# CI 应该自动跑（如果配了 GitHub Actions）
# → https://github.com/huisystems/bookrec/actions
```

## 反爬修复完成后再推 tag

等反爬修复 + smoke 重跑通后，再用：
```bash
git push origin v0.2.2
```

这会触发 publish workflow → 推 TestPyPI。
