# 能源用量校核助手

本地 HTML 工作台读取能源用量 Excel，对 2026、2025 年基础信息表按能源类型计算标准煤和二氧化碳，并与表内登记值按相对误差阈值核对。输入工作簿只读，不会被应用改写。

## 运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python energy_summit_assistant.py
```

运行后会弹出控制窗口，并自动在 Chrome 新窗口中打开 HTML 页面；Windows 会将该页面窗口移动到主显示器并最大化。控制窗口可再次打开能耗统计页面，或点击“退出当前程序”关闭服务。将待校核工作簿放入 `input/`，并在 `config.yaml` 的 `app.input_path` 指定相对路径。

## 配置

- `config.yaml`：本地服务、工作簿路径、相对误差阈值、展示顺序及计算系数。
- `AI.env`：用户维护的本地 AI 模型配置；当前第一阶段校核不调用 AI。
- `input/`：本地 Excel 数据目录，默认不纳入 Git。

容差默认是 1% 相对误差：`abs(复算值 - 表内值) / abs(表内值) <= 1%`。表内值为 0 时，只有复算值也为 0 才视为一致。
原工作簿中的空白数量和结果单元格按 0 参与计算与一致性判断。

## 计算口径

当前规则来自用户提供的公式截图。单位换算后的系数见 `config.yaml`。电力、汽油、柴油和天然气按实物量乘对应系数；热力及生活热水按吉焦口径计算。自来水、中水、冷量不计入标准煤；热力、生活热水、自来水、中水和冷量不计入二氧化碳汇总。Excel 当前没有热力计费方式字段，因此首版无法区分面积收费、蒸汽计量和生活热水水量计费，按表内“热力（吉焦）/生活热水（吉焦）”单位选择吉焦系数。

原始工作簿中的空白数量和结果单元格按 0 参与复算和一致性判定。月度动态汇总按当前表格显示的记录计算。可在月份、三级单位、能源类型表头筛选；单位名称保留工作簿原始值。标准煤复算值和总复算值都为 0 的记录默认隐藏，可勾选工具栏选项显示。

## 文档

- [能源校核流程与计算口径](docs/ENERGY_CHECK_WORKFLOW.md)
- [HTML 表格交互原则](docs/HTML_INTERACTION_PRINCIPLES.md)
- [跨平台开发规范](docs/CROSS_PLATFORM_PROGRAMMING.md)
- [GitHub 与群晖同步约定](docs/GitHub.md)
- [通用项目结构约定](docs/COMMON_PROJECT_SKILLS.md)

## 项目结构

```text
energy_summit_assistant.py           本地 HTML 服务启动入口
config.yaml                          本地应用与计算配置
logging_config.py                    统一日志配置
requirements.txt                     Python 运行依赖
src/energy_submit_assistant/modules/ Excel 读取、规则核算
src/energy_submit_assistant/flows/   校核工作流
web/                                 HTML、CSS、浏览器交互
docs/                                项目规范与设计文档
input/                               本地输入工作簿（不提交）
```
