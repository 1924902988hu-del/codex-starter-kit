---
name: starter-scrapling
description: 使用隔离的 Scrapling 环境读取公开 HTML 网页并提取正文；适用于用户给出公开链接或资料核验，不适用于登录页、浏览器操作、PDF 或验证码。
---

# 公开网页读取

优先检查本机 runtime：默认位于用户主目录 `.local/share/codex-starter-kit/scrapling`。Unix 使用 `bin/python`，Windows 使用 `Scripts/python.exe`。缺少环境时说明未配置，不声称已经抓取；用户授权安装后按仓库说明设置依赖。

使用 `scrapling.fetchers.Fetcher.get(url, timeout=20)` 读取公开网页，检查 HTTP 状态与正文。保留来源和读取时间，只返回相关摘录。`page.css()` 返回集合，要先取具体元素再调用 `get_all_text(separator="\n", strip=True)`。不要把防护页或空页面当成功。

先搜索发现候选，再核验原文；Scrapling 不是搜索引擎。不为使用工具重复读取已有可靠原文。普通抓取不用浏览器；本包不安装浏览器引擎。遇到 JavaScript 页面、登录、验证码、专用文档或抓取失败，使用当前授权的合适工具并说明限制，不绕过访问控制。

安装本技能不授权对外发送私有文件、读取凭据、购买、发信或发布。
