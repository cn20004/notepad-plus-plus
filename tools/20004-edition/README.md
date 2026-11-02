# Notepad++ 20004 Edition — 首批增强工具

本目录是 **cn20004/notepad-plus-plus** Fork 的实际功能开发，不是已完成的 Windows 修改版。现阶段保留官方 Notepad++ 核心，提供一个 **Python 3.10+ 标准库** 本地辅助程序。原有 Notepad++ 安装不受影响。

## 已实现

- 文本空行清理、去重复行
- 提取手机号码、邮箱、网址
- 手机号/邮箱脱敏
- 微信/招生聊天 TXT 的规则关键词摘录（**不代表 AI 对话理解**）
- TXT/Markdown/JSON/CSV/LOG 跨目录关键词搜索
- 按日期和自定义磁盘目录创建日志草稿
- 调用**本机** Ollama 的 /api/generate 接口进行真正的 AI 总结
- 不默认覆盖已有文件；使用 --force 才允许覆盖
- 不收集或上传文档；仅 Ollama 操作发往指定本地地址

## Windows 立即使用

下载此文件夹或克隆仓库。确认已安装 Python 3.10 以上：

```powershell
py -3 tools/20004-edition/npp20004.py clean "D:\资料\原始.txt" -o "D:\资料\清理后.txt"
py -3 tools/20004-edition/npp20004.py redact "D:\资料\家长聊天.txt" -o "D:\资料\脱敏.txt"
py -3 tools/20004-edition/npp20004.py chat "D:\资料\家长聊天.txt" -o "D:\资料\沟通摘要.md"
py -3 tools/20004-edition/npp20004.py search "D:\知识库" --query "就业"
py -3 tools/20004-edition/npp20004.py daily-log --home "E:\443-mykb" --date 2026-11-02
py -3 tools/20004-edition/npp20004.py ollama "D:\资料\课程.txt" --model qwen2.5:7b -o "D:\资料\课程摘要.md"
```

### Notepad++ 内启动

1. 菜单 **运行 → 运行...**。
2. 输入（将脚本绝对路径改成自己的，路径中有空格必须加引号）：
   ```text
   cmd /k py -3 "D:\source\notepad-plus-plus\tools\20004-edition\npp20004.py" clean "$(FULL_CURRENT_PATH)" -o "$(CURRENT_DIRECTORY)\$(NAME_PART)_clean.txt"
   ```
3. 点击“保存”，命名为 **20004 清理文本**，可选快捷键。
4. 其他操作将 clean 换成 chat 或 redact，输出文件名要相应修改。

注意：先保存当前文档；该命令读取磁盘文件而非尚未保存的编辑器缓冲区。

## 开发路线与目前限制

这只是**第一批功能的实际代码**，目前尚未修改 Notepad++ C++ 窗口、菜单或品牌，也没有独立 EXE、AI 侧栏、账号管理、自动更新或 Windows 实机验收；60 项规划中的其他功能未完成。后续将增加原生 C++ 插件/面板、配置及迁移、CI 编译等。请不要把本分支作为可直接安装的 Notepad++ 发布版。

GPL 等上游许可遵循原仓库要求。

## AI 图形窗口（新增）

Windows 下载本目录并安装 Python 3.10+、Ollama，运行 `Start-20004-AI.cmd`。图形窗口可以打开本地 TXT/Markdown/JSON/CSV/LOG 文本、输入自定义指令、选择 Ollama 模型、生成结果并保存为新的 Markdown 文件。需要本地模型先安装，例如 `ollama pull qwen2.5:7b`。默认调用 `127.0.0.1:11434`，不启用云端 API。

注意：这是一个**独立桌面 AI 助手窗口**，目前并非 Notepad++ 进程内的原生停靠侧栏；需要依赖 Python 和 Ollama。Windows 构建工作流可以尝试生成 x64 开发版，但必须待 GitHub Actions 成功和实际 Windows 启动验收后才可称为可交付版本。打包的 `Notepad++.exe` 也可能需要额外运行资源，尚未确认可作为独立完整安装包使用。
