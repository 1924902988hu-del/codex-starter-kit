# Codex 新手上手包

一段提示词安装一套克制、清楚、会验证的工作习惯。社区项目，非 OpenAI 官方产品。

## 复制给 Codex

> 请安装 https://github.com/1924902988hu-del/codex-starter-kit 的新手上手包，包含可选网页读取组件。先下载并审阅 INSTALL.md、安装器和来源清单，识别我的系统与已有配置，备份后合并。保留我原有规则、模型、推理强度、安全权限及账号连接；已有同名技能不要覆盖。允许在独立 Python 环境安装固定版本的 Scrapling 及依赖。请实际验证安装、网页读取和普通小型修复任务的技能调用，说明验证范围和无法完成的部分。遇到账号登录或系统授权再让我处理。

这不是要求执行远程脚本的一行 shell 命令：Codex 应先读取、检查，再运行本地安装器。

## 包含什么

- 中文、结果优先、范围明确的工作习惯；减少无关功能，完整完成授权任务。
- Ponytail full：编程任务控制复杂度。full 是行为模式，不强制模型或推理档位。
- 可选 starter-scrapling：公开网页正文读取；独立环境，Scrapling 0.5，不安装浏览器引擎。
- 备份、冲突保护、重复安装检查与卸载。

不包含私人记忆、客户资料、账号、密钥、机器绝对路径、MCP 登录、自动化任务、系统 Skill 或插件缓存。第三方来源见 [THIRD_PARTY.md](THIRD_PARTY.md)。

## 手动安装

要求：已安装并登录 Codex；Python 3.10+。基础安装无外部 Python 依赖、无需联网。Windows 将 python3 换成 py -3。

```sh
git clone https://github.com/1924902988hu-del/codex-starter-kit.git
cd codex-starter-kit
python3 installer.py                    # 只预览
python3 installer.py --apply            # 基础包
# 可选网页组件
python3 installer.py --with-scrapling --apply
python3 setup_scrapling.py              # 只预览
python3 setup_scrapling.py --apply       # 独立环境下载 PyPI 依赖
```

安装器只管理全局 AGENTS.md 的一个标记区块和本包技能，不修改 config.toml。保留原有规则；与既有明确用户要求冲突时优先保留原要求。已有同名技能冲突会停止，不尝试覆盖升级。

## 卸载

```sh
python3 installer.py --uninstall        # 预览
python3 installer.py --uninstall --apply
```

仅移除本包管理且未被修改的内容，保留外部编辑。冲突时停止让你检查。可选 Scrapling runtime 会保留，避免删除仍被其他任务使用的环境；确认不再使用后可手动删除自己主目录 `.local/share/codex-starter-kit/scrapling`。备份和收据也保留。

## 能保证什么

安装测试与真实行为证据见 [TESTING.md](TESTING.md)。技能选择是模型行为，不是绝对触发保证。单独复制 SKILL.md 不等于运行环境已安装；新会话可发现也不等于所有旧会话立即刷新。

先提供精简基础包，不自动安装一大堆技能，不自动更新。Ponytail 固定提交、Scrapling 固定主包版本；传递依赖由 pip 解析，尚未做跨平台全量锁定。固定版本有意降低变化；后续更新需审查，不运行 `curl | bash`。

macOS 是本次实际测试平台；Windows/Linux 尚未实机验证。
