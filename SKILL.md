---
name: intranet_browser_10_25
description: OpenClaw browser skill for http://10.81.73.9:10000/
metadata: {"openclaw":{"emoji":"🦞","homepage":"https://docs.openclaw.ai/tools/browser"}}
---

# OpenClaw（小龙虾）内网浏览器自动化

## 术语

- **「小龙虾」**：本技能中指 [OpenClaw](https://docs.openclaw.ai/tools/browser) 及其 **browser** 能力，不是泛指 Playwright。
- **默认站点**：`http://10.81.73.9:10000/`。Gateway / 浏览器进程所在机器必须能路由到该地址（内网或 VPN）。

## 登录页形态（当前系统）

- **布局**：浅蓝底、居中竖向表单；自上而下一般为 **账号**（人像图标）、**密码**（锁图标，可有显示/隐藏小眼睛）、**验证码**（盾牌图标 + 占位「请输入验证码」）、右侧 **图形验证码图片**（多位数字 + 干扰线，常见为 **canvas**）、「忘记密码?」链接、底部蓝色 **「登录」** 按钮。
- **自动化要点**：除账号密码外还有 **图形验证码**。Agent 不得把用户截图或对话里的密码写进仓库或日志。
- **OpenClaw**：`snapshot` / `screenshot` 后由用户 **口述当前验证码** 再 `act` 填入验证码框并点「登录」；或 headed 下由用户在浏览器里手输验证码（见 reference）。
- **Playwright 兜底（Node 模板）**：支持环境变量 `XIAO_LONG_XIA_CAPTCHA`；无验证码且 headless 时会报错提示（见 `scripts/automation-template.mjs`）。
- **Selenium Python（`auto.py`）**：优先 **`CHROMEDRIVER_PATH`** 或同目录 **`chromedriver_2.exe`** 驱动 **本机 Chrome**；若本地驱动与 Chrome **主版本不一致**，脚本会 **自动改用 Selenium Manager** 下载匹配驱动（需外网）。无本地驱动时亦走自动匹配。`canvas` 用 **ddddocr** 识别验证码，失败则手输。详见下文「与 `auto.py` 对齐的流程」。

### 与 `auto.py` 对齐的 DOM / 选择器（登录）

实现与 `{baseDir}/../auto.py`（工作区中与 `openclaw-intranet-browser` 同级的 `auto.py`）一致，便于 Agent 在无 browser 工具时用脚本复现，或在 OpenClaw 中手写等价步骤：

| 步骤 | 定位方式 |
|------|-----------|
| 用户名 | `input.xl-input__inner[placeholder="请输入用户名"]` |
| 密码 | `input.xl-input__inner[type="password"]` |
| 验证码 | `get_by_placeholder("请输入验证码")`；验证码图多为 **canvas**（见下） |
| 登录 | `get_by_role("button", name="登录")` |

- **验证码 canvas**：`page.locator("canvas")`；优先选 **可见** 且 **面积最大**（宽×高 ≥ 约 1500）的一块截图 OCR；若无满足阈值的，则对第一个可见 canvas 截图。
- **登录后等待**：`wait_for_load_state("networkidle")`；`auto.py` 会等待 **顶部搜索** `div.header-search-trigger` 或侧栏 `div.xr-menu[role="menu"]` 出现（最长约 120s），超时则跳过打开画面。

## 登录后：顶部全局搜索（`auto.py`）与左侧导航（`xr-menu` / OpenClaw）

### `auto.py`：画面名称 → 顶部搜索

- 检测到主界面后、点搜索前：`document.readyState === complete`，轮询 **loading 遮罩** 消失；若存在 **`div.xr-menu`**，则最多约 **25s** 等待侧栏菜单节点 **≥5**（表示树已渲染）；再 **`AUTO_POST_LOGIN_DWELL_SEC`（默认 8s）** 静置。打开搜索后若无 **`span.search-item-title`** 或出现 **「无匹配」**，会 **清空重输** 轮询最多 **`AUTO_SEARCH_MAX_RETRIES`（默认 15）** 次。
- 点击 **`div.header-search-trigger`**（含「搜索」与 Ctrl+K 提示）。
- 选中结果进入业务页后：`readyState` + loading 遮罩 + **`AUTO_OPENED_PAGE_DWELL_SEC`（默认 3s）**；再点左下 **`div.left-auth-button-box`** 内 **`button[id*='authButton-F2']`**（如 `SMCR03V-authButton-F2`，子级 `span.buttonNameBox` 为 F2、`span` 为 查询），失败再试文案 XPath，最后 **`body` + F2** 快捷键。
- 在弹层/浮层中的 **`input.xl-input__inner`**（或等价）输入用户给出的 **关键词**（可与完整菜单标题为 **子串** 关系，如 `冷轧热卷入库管理` 对应 `WMCRHRX11P1-冷轧热卷入库管理` 类结果）。
- 等待 **`span.search-item-title`** 出现；优先点击 **标题文本包含关键词** 的第一条对应 **`div.search-item`**；若无包含关系则点 **列表第一条**。
- **留空**：登录后不打开其它画面。

### 左侧导航（`xr-menu`，OpenClaw / 手工）

- **形态**：深蓝底竖向侧栏；`div.xr-menu[role="menu"]`，项为 `li.xr-sub-menu` / `div.xr-sub-menu-content__title span` 等。
- **OpenClaw**：`snapshot` 后用 **ref** 点与界面完全一致的文案；多级菜单分步 `act`。

**可见的一级菜单名称**（自上而下，便于口述）：成本管理、应用集成平台、系统开发管理、工厂建模、工厂监控、采购管理、销售管理、出厂管理、财务管理、铁区管理、资源管理、质量管理、质量先期策划、智慧质量、生产合同管理、作业计划管理、物料管理。完整子菜单名以实际为准，见 [reference.md](reference.md)。

## 登录后：页签（`span.tab-name`）

- **场景**：进入某菜单后，主区顶部常有多个 **页签**；完整标题可能带方括号代码，例如 `冷轧热卷入库管理[WMCRHRX11P1]`。
- **`auto.py`**：不处理页签；需在浏览器内手动切换，或改用 OpenClaw / 自写步骤。
- **OpenClaw**：`snapshot` 后对用户给出的关键词找对应 tab 的 ref 再 `act`；注意子串不必等于全称。

## 业务页示例：查询条件 + 明细表（仓库图形化类页面）

典型布局为上下两块（浅蓝企业风）：

- **查询条件**：分区标题多为 **「查询条件」**。常见字段：**库区号**（下拉）、**库业务类型**、**材料号**、**牌号(钢级)**、**合同号**、**机组代码**（下拉）、**事件发生时间**（起止日期时间，如 `2026-04-14 00:00:00`～`2026-04-24 23:59:59`）。另有 **红冲/准发类** 页面：**库区号带 `*` 为必选**，须先选库区再点左下 **F2查询**，否则表内长期 **「无相关数据」**（详见 [reference.md](reference.md)「红冲 / 准发类查询页」）。
- **详细信息显示**：表格区；无数据时显示 **「无相关数据」**。表头常含：起始库区号、库区号、材料号、库业务类型、出入库时间、出入库区分、材料形态标志、合同号、材料实际厚度/宽度/长度等（以当前版本为准）。
- **提交查询**：底部左侧 **「F2查询」** 按钮；部分实现同时支持键盘 **F2** 触发查询。表格区常见 **Excel 导出** 图标与底部分页（每页条数、总条数）。
- **自动化**：OpenClaw 用 `snapshot` 对 ref 填表、点「F2查询」；下拉与时间范围需在每次 snapshot 后确认选项已展开。字段级定位与 F2 说明见 [reference.md](reference.md)，Playwright Node 兜底见 `fillForm()` 注释。

## 扩展本技能：页面打开后「填什么、点哪里」（OpenClaw）

### `snapshot` 与「整页 HTML」

- OpenClaw 的 **`snapshot`** 给 Agent 的通常是 **带 ref 的控件树 / 可访问性信息**，用来 **`act(ref)`** 输入、点击；**并不等价于**在对话里贴完整 `outerHTML`。
- 要让模型稳定操作，技能里应写清：**分区标题**（如「查询条件」）、**占位符 / 标签文案 / 按钮可见文字**、必要时 **CSS 备用**（与 `auto.py` 同源），而不是依赖「自己猜 HTML」。

### 推荐往 `SKILL.md` 或 `reference.md` 里加的内容

1. **触发**：在 YAML **`description`** 里加业务关键词（便于匹配用户说法）；正文写「当用户要 … 时」。
2. **按画面拆小节**：如何识别已进入该页（URL 片段、独有标题、表格区文案）。
3. **操作表模板**（每个业务页可复制一张）：

| 顺序 | 动作 | 数据从哪来（用户 / 默认 / 上一步） | snapshot 里怎么认（标签、placeholder、按钮名） | 备注 |
|------|------|--------------------------------------|--------------------------------------------------|------|
| 1 | 输入 | … | … | 填完可略等防抖 |
| 2 | 点击 | … | … | 下拉先展开再 snapshot |

4. **硬性约定（写给 Agent）**：**每次 `act` 后若 UI 会变（出现新 ref、弹层、表格刷新），必须再 `snapshot`**；**下拉、日期范围**先点开展示选项，再 snapshot 点具体项。
5. **篇幅**：字段字典、多画面枚举放 **`reference.md`**；`SKILL.md` 只保留 **流程 + 最关键几条**，避免技能过长稀释重点。

### Agent 执行循环（与官方 Browser 文档一致）

`navigate` → **`snapshot`** → 对照技能中的表与用户意图 → **`act(ref)`** →（界面变化）→ **`snapshot`** → …；拿不准时用 **`screenshot`** 辅助。

### 与 `auto.py` 的分工

- **OpenClaw**：表单组合多、常改 UI → **扩展本节的文字说明 + 表**，靠 snapshot/act 适配。
- **`auto.py`**：固定步骤（如当前登录→搜索→F2）→ 改 Python；选择器可与上表 **对齐**，便于无 browser 工具时兜底。

## 优先：OpenClaw `browser` 工具

具备 **browser** 工具时，用 **navigate → snapshot → act(ref)** 完成全流程，避免先写长脚本。

1. **Profile**：默认用托管隔离的 `openclaw` profile；仅在用户明确要求且可接受本机 Chrome 附加/授权时，再用 `user` 等以复用已登录会话（见官方 Browser 文档）。
2. **步骤**：`navigate` 打开 URL → `snapshot` 取控件 **ref** → `act` 点击/输入 → 菜单与表单每步后按需再 `snapshot`；必要时 `screenshot` 排错。
3. **内网**：若 Gateway 访问不到 `10.25.*`，把带浏览器的 **host / node** 部署到可达网段，或调整 `target` / 远程 CDP（见文档）。

## 兜底：Playwright

无 browser 工具时，任选其一（内网可达、已安装依赖）：

### Node：`{baseDir}/scripts/automation-template.mjs`

说明见 [reference.md](reference.md)。

### Python：`auto.py`（与上表选择器 / 登录后顶部搜索一致）

- **路径**：通常与工作区根目录 `auto.py` 一致；若技能单独克隆，请将同逻辑脚本放在可执行路径或从仓库复制。
- **环境**：

```text
pip install -r requirements-auto.txt
```

`requirements-auto.txt` 含：`selenium`、`ddddocr`（OCR 可选；未安装则仅手输验证码）。**无需** `playwright install`。驱动：可选同目录 **`chromedriver_2.exe`** 或 **`CHROMEDRIVER_PATH`**；版本不匹配时脚本会回退 **Selenium Manager**（需外网）。亦可删除旧驱动仅依赖自动下载。

- **交互输入**：
  1. **访问网址**（回车默认 `http://10.81.73.9:10000/`；若手输可不带协议，脚本会补 `http://`）；
  2. **账号** / **密码**（回车分别默认 `195141` 与脚本内配置；密码行用 `getpass` 不回显）；
  3. **画面名称**：顶部搜索关键词（结果 `span.search-item-title` 子串匹配优先，否则第一条）；留空则登录后不打开其它画面。非空时进入画面后会 **等待业务页加载** 并 **执行 F2 查询**（按钮或快捷键）。
- **运行**： headed 本机 Chrome；启动参数忽略证书错误（等价于原 Playwright `ignore_https_errors`）；页面加载与显式等待最长约 60～120s。
- **失败**：异常时全页截图 **`auto_login_error.png`**（勿提交 git）；结束前会提示「按回车关闭浏览器」。
- **Windows 控制台**：脚本尝试将 stdout/stderr 设为 UTF-8，减少中文乱码。

## 原则

- 凭据只来自 OpenClaw secrets、环境变量或用户当次提供，**禁止**写入仓库与 SKILL。
- 失败时：OpenClaw 用 `screenshot`；Node 脚本写 `openclaw-fallback-error.png`；Python 写 `auto_login_error.png`。

## Agent 约定

- **有 OpenClaw**：用 snapshot 的 ref 完成登录、顶部搜索或侧栏点菜单、填表；对齐用户给出的 **画面名称** 与字段名；`auto.py` 用顶部搜索子串匹配打开画面。
- **无 OpenClaw**：在可达内网环境执行 `automation-template.mjs`，或执行 **`auto.py`**（需要图形验证码时优先 headed + ddddocr 或手输）。

## 延伸阅读

- [reference.md](reference.md)
