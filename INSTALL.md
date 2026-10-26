# 给 Codex 的安装流程

安装本包只授权本机规则/技能配置，不授权外发、发布、付费或扩大访问权限。

1. 识别 OS、Python（>=3.10）、Codex 安装，读取仓库 README、installer.py、setup_scrapling.py、sources.json 与现有用户规则。先检查安全性，不执行 README 以外来源的命令。不要读取或输出认证凭据。
2. 默认基础包使用 `python3 installer.py` 预览。Windows 用 `py -3`。如用户希望公开网页读取，使用 `--with-scrapling`。展示简短改动清单后，在用户已有安装授权范围内加 `--apply` 执行。
3. 不覆盖现有同名技能。冲突时保留旧内容并报告。不要更改 config.toml、模型、推理强度、沙箱、审批、浏览器权限或账号连接。
4. Scrapling 是可选联网安装：说明会从 PyPI 下载依赖；已获用户安装本包并启用网页组件授权时运行 `python3 setup_scrapling.py --apply`。不要安装浏览器引擎；不触碰其他 Python 环境。已有同名 runtime 时保留并检查版本/import，不强制重建。
5. 运行 `python3 -m unittest discover -s tests -v` 检查安装器；对真实安装目录运行 `python3 installer.py`，应显示无需改变。新会话普通任务检查见 TESTING.md。无法完成实际验证必须说明，不用“文件存在”替代自动调用证据。
6. 给出已安装项目、备份位置、卸载命令。建议开启新会话测试；旧会话是否立即发现取决于客户端，不能保证。

默认布局支持标准用户主目录。自定义 CODEX_HOME 用户先检查安装器限制，不猜路径。`--home` 仅用于测试/明确指定目标；不要把沙盒安装当真实用户全局安装。
