# 首次配置

1. 核对 Python 3.9+、Git、GitHub CLI、Hugo Extended、lark-cli。缺失时优先用官方安装途径；GitHub 用 `gh auth login`，飞书先看 `lark-cli --help` 及 `lark-cli docs +fetch --help`，按当前 CLI 指引登录并授权读取文档与图片。登录由用户在官方界面完成，不索取 Token。用 `gh api user --jq .login` 和实际读取用户指定文档核对身份与访问权限。Hugo 使用与模板 Pages workflow 一致的版本。
2. 如用户已有 Lark2GhBlog 站，复用它；不要改造其其他站点。新建默认使用该账号下独立的 `blog` 项目仓库，站点地址 `https://OWNER.github.io/blog/`。公开 Pages 会公开文章和图片；首次让用户明确站点归属和公开范围，已明确要求在该账号搭建公开博客则直接继续。仓库重名时不覆盖。
3. 从 skill 目录运行 `python3 scripts/bootstrap.py /absolute/new-blog --owner OWNER --repo blog --author "展示名"`。进入生成目录，`git init -b main`，用 `git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod` 添加主题，并检出验证过的提交 `118119693d8b5ac211b939775678310973bcb232`（在主题目录检出后提交主仓库的子模块引用）。如果账号没有根个人站，可移除“个人主页”菜单项。主题和 Hugo 升级前先构建核验。
4. 若同时提供文章，先按发文参考导入和验证。构建 `hugo --gc --minify`，检查首页和待发布页面。只提交生成站点的源码、主题引用和批准公开的文章资源。使用 `gh repo create OWNER/blog --public --source . --remote origin --push`，确认远端 main 已存在后用 `gh api --method POST repos/OWNER/blog/pages -f build_type=workflow` 启用 Pages。若首次构建早于 Pages 初始化而失败，核对失败原因及设置后重跑同一次工作流。若返回超时，先读回仓库或 Pages 状态再决定是否重试。
5. 按发文参考核对线上结果。在站点仓库的 README 记录该站归属、地址、默认分支、`git clone --recurse-submodules` 及后续发文用法；用户以后打开这个项目发链接，目标就能从当前仓库识别。新项目或不相关工作区无法识别站点时，只问目标仓库或本地路径。

6. 用户明确选择以后在这个项目“发链接即公开发布”时，可在站点根目录的本地忽略文件 `.lark2ghblog-local.json` 记下 `{"repository":"OWNER/blog","publish_on_link":true}`。仅当文件里的仓库与实际远端及用户身份相符时，才把该项目中的裸链接视为发文请求。用户关闭时更新此项；不要跨仓库沿用，也不要提交该文件。换电脑或换项目时重新明确目的地和该偏好。
