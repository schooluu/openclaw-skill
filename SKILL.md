---
name: intranet_browser_10_25
description: OpenClaw browser skill for http://10.25.145.37:10003/ — login with graphical CAPTCHA, xr-menu sidebar, span.tab-name tabs, forms. Triggers 小龙虾, OpenClaw, intranet 10003, 内网自动化. Playwright Python auto.py：交互登录、ddddocr 画布验证码、英文逗号多级菜单、页签子串匹配。
metadata: {"openclaw":{"emoji":"🦞","homepage":"https://docs.openclaw.ai/tools/browser"}}
---

# OpenClaw（小龙虾）内网浏览器自动化

## 术语

- **「小龙虾」**：本技能中指 [OpenClaw](https://docs.openclaw.ai/tools/browser) 及其 **browser** 能力，不是泛指 Playwright。
- **默认站点**：`http://10.25.145.37:10003/`。Gateway / 浏览器进程所在机器必须能路由到该地址（内网或 VPN）。

## 登录页形态（当前系统）

- **布局**：浅蓝底、居中竖向表单；自上而下一般为 **账号**（人像图标）、**密码**（锁图标，可有显示/隐藏小眼睛）、**验证码**（盾牌图标 + 占位「请输入验证码」）、右侧 **图形验证码图片**（多位数字 + 干扰线，常见为 **canvas**）、「忘记密码?」链接、底部蓝色 **「登录」** 按钮。
- **自动化要点**：除账号密码外还有 **图形验证码**。Agent 不得把用户截图或对话里的密码写进仓库或日志。
- **OpenClaw**：`snapshot` / `screenshot` 后由用户 **口述当前验证码** 再 `act` 填入验证码框并点「登录」；或 headed 下由用户在浏览器里手输验证码（见 reference）。
- **Playwright 兜底（Node 模板）**：支持环境变量 `XIAO_LONG_XIA_CAPTCHA`；无验证码且 headless 时会报错提示（见 `scripts/automation-template.mjs`）。
- **Playwright Python（`auto.py`）**：对页面上 **足够大且可见** 的 `canvas` 截图，用 **ddddocr** 自动识别；失败或未安装库则 **交互式手输验证码**。详见下文「与 `auto.py` 对齐的流程」。

### 与 `auto.py` 对齐的 DOM / 选择器（登录）

实现与 `{baseDir}/../auto.py`（工作区中与 `openclaw-intranet-browser` 同级的 `auto.py`）一致，便于 Agent 在无 browser 工具时用脚本复现，或在 OpenClaw 中手写等价步骤：

| 步骤 | 定位方式 |
|------|-----------|
| 用户名 | `input.xl-input__inner[placeholder="请输入用户名"]` |
| 密码 | `input.xl-input__inner[type="password"]` |
| 验证码 | `get_by_placeholder("请输入验证码")`；验证码图多为 **canvas**（见下） |
| 登录 | `get_by_role("button", name="登录")` |

- **验证码 canvas**：`page.locator("canvas")`；优先选 **可见** 且 **面积最大**（宽×高 ≥ 约 1500）的一块截图 OCR；若无满足阈值的，则对第一个可见 canvas 截图。
- **登录后等待**：`wait_for_load_state("networkidle")`；侧栏 `div.xr-menu[role="menu"]` 最长等待约 60s，超时则跳过菜单/页签步骤并提示。

## 登录后：左侧导航（`xr-menu` / `auto.py` 实现）

- **形态**：深蓝底竖向侧栏；DOM 为 `div.xr-menu[role="menu"]`，项为 `li.xr-sub-menu` / `div.xr-sub-menu-content__title span` 等（与 Element / 自研组件一致）。
- **多级路径（`auto.py`）**：用户在一步输入中用 **英文逗号** `,` 分隔每一级要点的 **菜单文案**（与界面 **完全一致** 的精确匹配）。脚本按顺序对每一级调用 `_click_sidebar_label`：
  1. 在 `div.xr-menu[role="menu"]` 内遍历 `div.xr-sub-menu-content__title span`，`inner_text().strip() == label` 则点击其祖先 `div.xr-sub-menu-content`；
  2. 若无匹配，则在侧栏滚动区 `.xl-scrollbar.xr-menu-scrollbar` 内 `get_by_text(label, exact=True)` 点击第一项。
- **每级间隔**：约 0.35s，避免动画未完成。
- **OpenClaw**：仍建议每步后 `snapshot`，用 **ref** 点与界面完全一致的文案（含简繁、空格、末尾字符如 `X`）；口述路径可与 `auto.py` 的逗号路径一一对应。

**可见的一级菜单名称**（自上而下，便于用户口述路径）：成本管理、应用集成平台、系统开发管理、工厂建模、工厂监控、采购管理、销售管理、出厂管理、财务管理、铁区管理、资源管理、质量管理、质量先期策划、智慧质量、生产合同管理、作业计划管理、物料管理。完整子菜单名以实际展开为准，见 [reference.md](reference.md)。

**嵌套示例（仓库 MMS）**：一级 **「仓库管理(MMS)X」** → 二级 **「仓库图形化」** → 叶子 **「仓库图形化显示_板坯」**。在 `auto.py` 中合并为一行：`仓库管理(MMS)X,仓库图形化,仓库图形化显示_板坯`。

## 登录后：页签（`span.tab-name`）

- **场景**：进入某菜单后，主区顶部常有多个 **页签**；完整标题可能带方括号代码，例如 `冷轧热卷入库管理[WMCRHRX11P1]`。
- **`auto.py` 行为**：用户输入 **子串**（如 `冷轧热卷入库管理`），脚本在 `span.tab-name` 中查找第一个 `inner_text` **包含** 该子串的节点，滚动可见后点击；找不到则报错。
- **OpenClaw**：`snapshot` 后对用户给出的关键词找对应 tab 的 ref 再 `act`；注意子串不必等于全称。

## 业务页示例：查询条件 + 明细表（仓库图形化类页面）

典型布局为上下两块（浅蓝企业风）：

- **查询条件**：分区标题多为 **「查询条件」**。常见字段：**库区号**（下拉）、**库业务类型**、**材料号**、**牌号(钢级)**、**合同号**、**机组代码**（下拉）、**事件发生时间**（起止日期时间，如 `2026-04-14 00:00:00`～`2026-04-24 23:59:59`）。
- **详细信息显示**：表格区；无数据时显示 **「无相关数据」**。表头常含：起始库区号、库区号、材料号、库业务类型、出入库时间、出入库区分、材料形态标志、合同号、材料实际厚度/宽度/长度等（以当前版本为准）。
- **提交查询**：底部左侧 **「F2查询」** 按钮；部分实现同时支持键盘 **F2** 触发查询。表格区常见 **Excel 导出** 图标与底部分页（每页条数、总条数）。
- **自动化**：OpenClaw 用 `snapshot` 对 ref 填表、点「F2查询」；下拉与时间范围需在每次 snapshot 后确认选项已展开。字段级定位与 F2 说明见 [reference.md](reference.md)，Playwright Node 兜底见 `fillForm()` 注释。

## 优先：OpenClaw `browser` 工具

具备 **browser** 工具时，用 **navigate → snapshot → act(ref)** 完成全流程，避免先写长脚本。

1. **Profile**：默认用托管隔离的 `openclaw` profile；仅在用户明确要求且可接受本机 Chrome 附加/授权时，再用 `user` 等以复用已登录会话（见官方 Browser 文档）。
2. **步骤**：`navigate` 打开 URL → `snapshot` 取控件 **ref** → `act` 点击/输入 → 菜单与表单每步后按需再 `snapshot`；必要时 `screenshot` 排错。
3. **内网**：若 Gateway 访问不到 `10.25.*`，把带浏览器的 **host / node** 部署到可达网段，或调整 `target` / 远程 CDP（见文档）。

## 兜底：Playwright

无 browser 工具时，任选其一（内网可达、已安装依赖）：

### Node：`{baseDir}/scripts/automation-template.mjs`

说明见 [reference.md](reference.md)。

### Python：`auto.py`（与上表选择器 / 菜单 / 页签一致）

- **路径**：通常与工作区根目录 `auto.py` 一致；若技能单独克隆，请将同逻辑脚本放在可执行路径或从仓库复制。
- **环境**：

```text
pip install -r requirements-auto.txt
playwright install chromium
```

`requirements-auto.txt` 含：`playwright`、`ddddocr`（OCR 可选；未安装则仅手输验证码）。

- **交互输入**：
  1. **访问网址**（可不带协议，脚本会补 `http://`）；
  2. **账号** / **密码**（密码用 `getpass`，不回显）；
  3. **菜单路径**：多级用 **英文逗号** 分隔；留空则登录后不点菜单；
  4. **页签关键词**：`span.tab-name` 子串；留空则跳过。
- **运行**： headed Chromium，`ignore_https_errors=True`，默认各类超时约 60s（页签查找 30s）。
- **失败**：异常时全页截图 **`auto_login_error.png`**（勿提交 git）；结束前会提示「按回车关闭浏览器」。
- **Windows 控制台**：脚本尝试将 stdout/stderr 设为 UTF-8，减少中文乱码。

## 原则

- 凭据只来自 OpenClaw secrets、环境变量或用户当次提供，**禁止**写入仓库与 SKILL。
- 失败时：OpenClaw 用 `screenshot`；Node 脚本写 `openclaw-fallback-error.png`；Python 写 `auto_login_error.png`。

## Agent 约定

- **有 OpenClaw**：用 snapshot 的 ref 完成登录、点菜单、填表；对齐用户口述的菜单名与字段名；菜单多级顺序与 `auto.py` 的逗号路径一致。
- **无 OpenClaw**：在可达内网环境执行 `automation-template.mjs`，或执行 **`auto.py`**（需要图形验证码时优先 headed + ddddocr 或手输）。

## 延伸阅读

- [reference.md](reference.md)
