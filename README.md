# Amadeus Presence

红莉栖个人桌宠原型。当前交付为桌面窗口和基础交互验证，不是完整 V0.1。

## 启动

当前电脑已经创建项目独立 `.venv` 后，可双击 **Start Amadeus.cmd**。

其他电脑需要 Python 3.10+，在项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

调试启动：

```powershell
.\.venv\Scripts\python.exe app.py --debug
```

## 操作

- 鼠标靠近面部：眼睛跟随，头部滞后；离远后小幅随机扫视。
- 左键点击：确认；10 秒内连续点击：逐步皱眉、偏头；不耐烦缓慢衰减。
- 按住左键拖动：移动角色，松开保存位置；拖动不会同时算作点击。
- 右键：调试面板、置顶开关、退出。
- 自然眨眼和微小呼吸持续运行；占位模型使用程序绘制，无需美术资源。

## 当前边界

已实现透明无边框窗口、拖动、置顶、位置保存、屏幕范围回收、typed 状态、事件分发、基础点击情绪、视线平滑、眨眼、调试窗口和本地交互日志。

尚未实现 Live2D、台词、完整 Reaction/Utility 评分、操作系统活动感知、拖动情绪、托盘、缩放或安装包。当前绘制与交互参数只用于原型验证。

启动后应用不发起网络请求，不读取窗口标题、键盘正文、进程或屏幕截图。位置和置顶选项写入项目 `.local/settings.json`；交互日志写入 `.local/events.jsonl`，约 1 MB 后轮换并只保留一份上一轮日志。短期情绪不跨重启保存。

## 结构

- `core/`：事件与状态。
- `character/`：独立于 Qt 的交互逻辑。
- `ui/`：桌面窗口与可替换的占位绘制。
- `storage/`：本地设置。
- `config/behavior.json`：当前行为参数。
- `assets/`：后续角色资源。

## 检查

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

手动验收：拖动后重启位置正确；快速连点有递进反应；普通拖动不增加点击次数；右键可以退出；透明区域不遮挡其他窗口；不同 DPI 和双屏下拖动可用。自动离屏测试不能替代 Windows 桌面合成与多屏实测。

下一步：先试玩占位原型，确定尺寸、动作速度和打扰程度，再选择临时立绘与 Live2D 制作方式。
