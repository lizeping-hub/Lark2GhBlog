# 导入与验收

1. 在目标站工作区检查 `git status --short --branch`、远端及部署设置。远端有更新时安全同步；遇到文章路径已有人工改动或无关变更，隔离处理，不覆盖或夹带提交。新站自带导入清单和校验脚本。旧 Hugo 站只有用户授权接入后才适配：保留其样式和配置，复用现有清单及 slug，检查 CI 是否依赖旧校验参数。对 wiki/docx 两种链接指向同一篇旧文的情况，先在已有清单补齐已确认的文档身份哈希（`document_key` 为文档 ID 的 SHA-256）再导入，避免重复。
2. 从 skill 目录运行 `python3 scripts/import_article.py '飞书URL' --site /absolute/blog --audit /absolute/private-audit/new-run`。每个链接用单独、尚不存在的审计目录，放在仓库外。工具按源文档身份复用文章路径，去掉分享参数；媒体以原始字节存入文章包。可一次处理多个链接，但在所有获准发布的文章通过验收前不要推送。公开前确认用户有权公开正文和图片；如果发现文档明显含内部资料或凭据，报告具体位置并暂停这篇，不擅自删改。发文许可不包含更改飞书权限。
3. 构建 `hugo --gc --minify`，对每篇运行 `python3 scripts/verify_import.py /absolute/private-audit/new-run --slug SLUG`。在 CLI 版本、嵌入内容、附件、画板或复杂表格不受支持时，先读回源文档定位具体缺项，必要时适配转换或请用户决定替代呈现；不要静默丢块或推送部分文章。首次站点额外检查导航与移动端。脚本报错、文件顺序或全文比对不符时不得发布。
4. 审查暂存范围与 diff。重复发送且没有实质变化时不造空提交，核对线上现有文章即可。提交并正常推送，禁止 force push；记录提交 SHA。用 `gh run list --repo OWNER/REPO --commit SHA` 找对应的 Pages workflow，再 `gh run watch RUN_ID --repo OWNER/REPO --exit-status`；不要把其他运行成功当成本次成功。
5. 以 Pages 实际 URL 核对文章的响应、正文及图文顺序（优先比较线上和本地生产构建页面；不完全一致时解析正文比对），逐图请求并比对 SHA-256。回报文章链接、部署结果和未能验证的事项。部署失败时查对应日志；没有明确证据不要重推或反复触发。用户只要求预览时停在本地校验。
