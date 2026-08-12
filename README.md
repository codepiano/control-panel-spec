# Project Tooling

面向 AI 的项目接入规范与脚手架。它帮助 AI 在理解一个已有代码仓库后，为该项目生成可维护、可验证的生命周期脚本、`control-panel.json` manifest，以及可选的运行时指标接口。

这个仓库不是通用脚本集合，也不是部署平台；它是一份让 AI 和项目代码库对“如何启动、停止、检查状态、打开主入口”达成一致的契约。

## 它解决什么问题

本地项目的启动方式往往各不相同：有的用 `npm run dev`，有的依赖 Python 环境、Docker、桌面应用或已有脚本。直接让 AI 猜测命令，容易得到不可重复、误伤其它进程的临时方案。

Project Tooling 规定了：

- 项目如何通过 `control-panel.json` 声明自己的控制入口
- AI 如何优先复用已有命令，而不是重新发明启动方式
- `init`、`install`、`start`、`stop`、`status`、`restart`、`uninstall` 的职责边界
- 如何识别并只管理项目自己的进程
- 如何用稳定的退出码和可选 metrics 接口报告运行状态
- AI 应返回什么形式的可审查改动

生成后的项目可被 [Control Panel](https://github.com/codepiano/control-panel) 自动发现和操作，但这份规范不依赖 Control Panel，也可以独立用于项目脚本治理。

## 给 AI 使用

将以下信息一起交给 AI：

1. 项目仓库或项目根目录
2. [Project Tooling Spec](./spec/PROJECT_TOOLING_SPEC.md)
3. 项目已有的启动文档、环境要求与业务约束
4. 已有的 `control-panel.json`、`scripts/` 或服务管理方式（如果存在）

可直接使用下面的提示词：

> 请先阅读 Project Tooling Spec，再检查当前项目。识别已有的运行入口、脚本、进程管理方式和工作目录；为项目生成或修复 `control-panel.json` 及实际需要的生命周期脚本。优先复用项目已有命令，脚本只能管理该项目自身的进程，状态检查必须可靠地区分运行与停止。最后返回最小化的 unified diff，并说明验证结果。

AI 应以项目自身的事实为准：规范提供边界和输出结构，不应覆盖项目已有的正确启动方式。

## 快速理解

一个接入后的项目通常包含：

```text
project-root/
  control-panel.json
  scripts/
    init.sh           # 可选：首次准备
    install.sh        # 可选：安装依赖
    start.sh
    stop.sh
    status.sh
    restart.sh
    uninstall.sh      # 可选：项目本地清理
    open-homepage.sh  # 可选：打开或聚焦主入口
```

最小 manifest 示例：

```json
{
  "id": "my-project",
  "name": "My Project",
  "workingDirectory": ".",
  "startCommand": "./scripts/start.sh",
  "stopCommand": "./scripts/stop.sh",
  "statusCommand": "./scripts/status.sh",
  "frontendUrl": "http://127.0.0.1:3000"
}
```

`statusCommand` 返回 `0` 表示运行或健康；非 `0` 表示停止、失败、降级或无法确认。具体退出码、字段优先级和进程归属规则以规范为准。

## 仓库内容

| 目录 | 用途 |
| --- | --- |
| [spec/](./spec/) | 给 AI 和项目维护者使用的正式规范 |
| [scaffolds/node/](./scaffolds/node/) | Node.js 项目的可复用 manifest、脚本和 metrics 模板 |
| [examples/](./examples/) | manifest 与 metrics 返回示例 |

当前只提供 Node.js 脚手架；其他运行时可以按同一生命周期和 manifest 语义扩展，不应复制出另一套协议。

## 使用边界

- manifest 是项目自身的唯一配置来源；控制界面可编辑展示字段，但不能建立独立的项目覆盖层。
- 生命周期脚本必须只操作项目拥有的进程，禁止以 `pkill node` 等全局方式处理进程。
- `start` 应当幂等，`stop` 对已停止项目应安全，`status` 必须给出可靠结果。
- metrics 应由项目自身或项目提供的适配器给出，不应根据主机上的猜测生成数据。
- 生成或修改脚本前，AI 应先读取项目中的现有入口、文档和约束。

## 开始使用

从 [Project Tooling Spec](./spec/PROJECT_TOOLING_SPEC.md) 开始。若项目是 Node.js 项目，可参考 [Node.js 脚手架](./scaffolds/node/) 和 [示例 manifest](./examples/control-panel.json)。

## 贡献

欢迎改进规范、示例和脚手架。新增运行时脚手架时，请保留同一份 manifest、生命周期、进程归属与 metrics 语义，并同时更新规范和示例。

## License

本仓库暂未声明开源许可证。在复用、发布或贡献前，请先与维护者确认许可方式。
