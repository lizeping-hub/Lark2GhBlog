# Lark2GhBlog

一个 Codex Skill：搭建自己的 Hugo + PaperMod 文章站，再把飞书或 Lark 云文档通过 GitHub Pages 发布出去。

## 安装

在终端运行：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/lizeping-hub/Lark2GhBlog.git ~/.codex/skills/lark2ghblog
```

如果已经安装，可在保留本地改动的前提下更新已有安装。若 Codex 尚未显示新技能，重新打开 Codex。

## 开始使用

1. 在 Codex 里说：“用 `$lark2ghblog` 帮我搭一个公开文章站，以后在这个项目里发飞书链接就发布。”
2. 按提示登录自己的 GitHub 和飞书账号。需要 Git、GitHub CLI、Python 3.9+、Hugo Extended 和 lark-cli；首次配置会检查这些工具。
3. 打开博客项目，在对话里发送飞书 Wiki 或 docx 链接。Skill 会导入正文与图片、构建核对，再推送并检查线上页面。再次发送同一篇文档的链接会更新原文章。

发布会公开文章和图片。请只提交有权公开的内容。这个 Skill 在对话中触发，不会在后台监控飞书。遇到不能完整迁移的嵌入内容时，先确认处理方式再发布。

## 许可证

本仓库源码采用 [MIT](LICENSE)。使用者发布的文章和图片不因使用本 Skill 而自动适用该许可证。PaperMod 在搭站时单独获取，遵循其自身许可证。
