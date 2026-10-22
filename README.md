# Project Tooling

面向 AI 的项目接入规范与脚手架。它帮助 AI 在理解一个已有代码仓库后，为该项目生成可维护、可验证的生命周期脚本、`control-panel.json` manifest，以及可选的运行时指标接口。

这个仓库不是通用脚本集合，也不是部署平台；它是一份让 AI 和项目代码库对“如何启动、停止、检查状态、打开主入口”达成一致的契约。

## 它解决什么问题

本地项目的启动方式往往各不相同：有的用 `npm run dev`，有的依赖 Python 环境、Docker、桌面应用或已有脚本。直接让 AI 猜测命令，容易得到不可重复、误伤其它进程的临时方案。

Project Tooling 规定了：

- 项目如何通过 `control-panel.json` 声明自己的控制入口
- 网络服务如何先注册本机 TCP 端口，再同步真实启动配置、访问地址与生命周期脚本
- 外层项目如何用 `children` 描述子项目路径、角色和归属原因；纯集合使用 `kind: collection`
- 项目如何用仓库内的相对路径声明跨控制界面复用的图标
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
| [SKILL.md](./SKILL.md) | 本仓库自身的 AI Skill，负责按规范检查、生成和验证项目接入 |

当前 Skill 以 Node.js、TypeScript 和 Electron 项目为主要执行场景；其他运行时可以按同一生命周期和 manifest 语义扩展，不应复制出另一套协议。

## 使用边界

- manifest 是项目自身的唯一配置来源；控制界面可编辑展示字段，但不能建立独立的项目覆盖层。
- 生命周期脚本必须只操作项目拥有的进程，禁止以 `pkill node` 等全局方式处理进程。
- `start` 应当幂等，`stop` 对已停止项目应安全，`status` 必须给出可靠结果。
- metrics 应由项目自身或项目提供的适配器给出，不应根据主机上的猜测生成数据。
- 生成或修改脚本前，AI 应先读取项目中的现有入口、文档和约束。

## 开始使用

从 [SKILL.md](./SKILL.md) 开始，规范正文位于 [Project Tooling Spec](./spec/PROJECT_TOOLING_SPEC.md)。

## 安装 Skill

Skill 目录需要直接包含 `SKILL.md`。默认安装位置是 `$CODEX_HOME/skills`；如果没有设置
`CODEX_HOME`，使用 `~/.codex/skills`。

### 本地开发链接

适合持续修改这个仓库的情况。链接后，仓库中的修改会直接成为 Skill 的修改：

```bash
SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$SKILLS_DIR"
ln -s "/Users/codepiano/git/control-panel-spec" "$SKILLS_DIR/project-tooling"
```

目标路径已存在时，先确认它不是正在使用的 Skill，再手动处理冲突，不要覆盖未知目录。

### 固定副本

适合把某个版本安装到其他机器或项目环境：

```bash
SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$SKILLS_DIR/project-tooling"
cp -R /path/to/project-tooling/. "$SKILLS_DIR/project-tooling/"
```

如果从私有 GitHub 仓库安装，可以先克隆，再执行上面的复制步骤：

```bash
git clone git@github.com:codepiano/control-panel-spec.git /path/to/project-tooling
```

安装后，在新的 Codex 任务中使用：

```text
$project-tooling 为当前项目生成或修复项目接入脚本
```

验证 Skill 包结构：

```bash
cd /path/to/project-tooling
python3 /Users/codepiano/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
./scripts/check-spec-sync.sh
```

如果 Skill 列表没有立即出现，重新加载 Codex 后再使用 `$project-tooling`。

## 贡献

欢迎改进规范和 Skill 工作流。新增运行时支持时，请保留同一份 manifest、生命周期、进程归属与 metrics 语义。

## License

本仓库暂未声明开源许可证。在复用、发布或贡献前，请先与维护者确认许可方式。

## 端口注册与协议获取

使用 `$project-tooling 为当前服务注册端口，并按 spec 生成或修复生命周期脚本`。
Skill 会检查项目已有入口，通过本机面板串行分配并持久化端口，随后生成项目适用的脚本。
停止的服务仍保留端口分配；真实监听配置与 manifest 地址必须一致。

```bash
node /path/to/project-tooling/scripts/port-registry.mjs spec
node /path/to/project-tooling/scripts/port-registry.mjs list
node /path/to/project-tooling/scripts/port-registry.mjs register --project /absolute/project --count 2
```

先创建含 `name` 和 `workingDirectory` 的最小 manifest。注册会保留其它字段、写入 `ports`，并将尚未发现的项目加入本机扫描入口。
已有端口可使用 `--ports 4323,4324` 请求，冲突直接失败。面板地址默认 `http://127.0.0.1:4310`，可通过 `CONTROL_PANEL_URL` 或 `--panel-url` 指定。
协议获取可离线执行，注册需要支持该 API 的运行中面板。完整流程见 [端口注册](./references/port-registration.md)。

## 项目内的 tunnel 与外部进程

Tunnel 是所属项目的子服务，用父 manifest 的 `children` 声明。
`scaffold-launchd.py` 为已有 LaunchAgent 生成项目自有的启动、停止、状态和重启脚本，
无需面板写死服务名，也不依赖运行时安装 Skill。停止使用 bootout，避免 KeepAlive 立即拉起。
生成命令和验收步骤见 [LaunchAgent 子服务接入](references/launchd-components.md)。


## 版本化生命周期（1.11）

可选 `release.protocol: 1` 与 `scripts.version/prepare/activate` 让消费者先隔离准备目标版本，
成功后停止旧进程、切换不可变产物，再核验实际运行版本。未适配项目保持原有生命周期。
详细 JSON、失败语义和项目接入验收见 [规范第 10 节](spec/PROJECT_TOOLING_SPEC.md)。
