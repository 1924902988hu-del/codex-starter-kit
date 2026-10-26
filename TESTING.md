# 验证记录与复现

2026-10-26，macOS arm64 / Python 3.14。

## 安装器：17 项测试通过

```sh
python3 -m unittest discover -s tests -v
```

覆盖：默认零写入、保留已有 AGENTS/config/auth、重复安装、冲突预检、哈希备份、不认领已有同内容技能、修改后拒绝卸载、保留区块外用户编辑、符号链接拒绝、I/O 回滚、卸载重装、基础包追加网页组件，以及运行时安装失败清理。

## 真实安装与技能调用

在新建测试主目录安装基础包和网页组件，从 PyPI 创建全新独立 Scrapling 0.5 环境，import 成功。随后启动两个没有父会话历史的 Codex CLI 会话，使用测试 HOME/CODEX_HOME，只有本包规则及技能。模型/推理沿用当前用户设置；为测试认证临时引用现有本机登录，结束后移除引用，没有把认证放入仓库。

普通编程请求未提技能名：
> normalize_label 遇到连续空白和制表符时结果不正确。请修复，保留其他行为并运行现有验证；只改需要修改的代码。

日志显示主动读取测试主目录中的 Ponytail，修复一个函数，现有测试 PASS，未增加依赖。

普通网页请求未提技能名：
> 请读取 https://example.com 的网页正文，用中文说明用途和实际读取是否成功。不需要修改文件。

日志显示主动读取 starter-scrapling，调用测试主目录的独立 Python 执行 Fetcher.get，HTTP 200，正文非空。

第一次网页测试因 workspace sandbox 禁止网络而 DNS 失败，并诚实回退；第二次仅为测试进程允许网络后成功。安装包不会修改使用者沙箱/权限，受限环境需要使用者批准联网。

最终两个 Skill 均通过 Codex quick_validate。Ponytail 保留原正文，只移除验证器不接受的 argument-hint 元数据；行为测试发生在该元数据清理前，清理后安装单测和元数据验证再次通过。

脱敏证据：[behavior.json](evidence/behavior.json)、[verification.json](evidence/verification.json)。原始会话日志不公开。

## 边界

这证明本机全新配置目录可安装和自动调用，不代表独立新账号注册流程、Windows/Linux 实机、全部模型或每个旧会话都已验证。技能自动选择并非硬性保证；安装后应新建会话做相同普通任务检查。

卸载测试覆盖规则与技能。网页 runtime 有意保留，需确认不再使用后手动移除；没有后台浏览器需要关闭。
