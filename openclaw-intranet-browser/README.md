# OpenClaw 技能：内网浏览器自动化（小龙虾）

本目录为 **单个 OpenClaw 技能**，可与控制里的 **「从 GitHub 导入」** 配合使用。

## 导入步骤

1. 在 GitHub 新建 **公开** 仓库，把本目录下的全部文件推到仓库 **根目录**（保证根目录有 `SKILL.md`）。
2. 在 OpenClaw 控制界面「从 GitHub 导入」的 URL 框填入：  
   `https://github.com/<你的用户名>/<仓库名>`  
   （须为 `https`，与官方 `openclaw skills add <url>` 行为一致。）
3. 导入成功后，新开会话或按文档刷新技能列表；确保已启用 **Browser** 相关能力后再让 Agent 操作内网页。

## 仓库布局要求

OpenClaw 按 [AgentSkills 兼容格式](https://docs.openclaw.ai/skills) 解析：技能根目录内必须有 `SKILL.md`，YAML 头中的 `name`、`description` 为必填；`metadata` 需为 **单行 JSON**（本技能已按此书写）。

## 可选：命令行安装

若使用 CLI：`openclaw skills add https://github.com/<用户>/<仓库>`（具体以你安装的 OpenClaw 版本文档为准）。

## 凭据与验证码

账号、密码、**图形验证码**不要写进仓库。脚本支持：

- `XIAO_LONG_XIA_USER` / `XIAO_LONG_XIA_PASS`
- `XIAO_LONG_XIA_CAPTCHA`：当前图片上的验证码（易过期，适合单次跑）
- `HEADLESS=0` 且不设验证码变量时，会在登录步骤 `pause()`，便于手输验证码

OpenClaw 场景下更推荐：用户看屏读验证码，由 Agent 通过 `act` 填入。

## 怎么测试

### A. 测 OpenClaw（小龙虾）里能不能用

1. **导入技能**：按上文把本目录推到 GitHub 公开库，在控制里「从 GitHub 导入」粘贴仓库 HTTPS；或本机执行文档中的 `openclaw skills add <url>`（以你版本为准）。
2. **确认技能已加载**：在终端执行 `openclaw skills list`（若命令名不同，以 [OpenClaw 文档](https://docs.openclaw.ai/skills) 为准），列表里应出现 `intranet_browser_10_25` 或你改过的 `name`。
3. **确认浏览器可用**：Gateway / 本机已按文档打开 **browser**（托管浏览器或 Chrome 附加等）；能访问 `http://10.25.145.37:10003/` 的机器须与浏览器同一网络（内网或 VPN）。
4. **新开会话**：对 Agent 用自然语言下任务，例如：「按 intranet_browser_技能：打开默认站点，等我报验证码后登录，再进仓库图形化显示_板坯，在查询条件里填材料号 xxx 并点 F2 查询。」验证码建议由你看图口述，避免把密码写进聊天日志。
5. **排错**：失败时看 Gateway 日志、控制里的浏览器截图；必要时在文档链接处核对 `browser` 的 `profile` / `target`。

### B. 测 Playwright 兜底脚本（不经过 OpenClaw）

在 **能访问该内网 IP** 的电脑上：

```powershell
cd openclaw-intranet-browser\scripts
npm init -y
npm i playwright
npx playwright install chromium
```

```powershell
$env:XIAO_LONG_XIA_USER="你的账号"
$env:XIAO_LONG_XIA_PASS="你的密码"
$env:XIAO_LONG_XIA_CAPTCHA="当前验证码四位"
$env:HEADLESS="0"
node .\automation-template.mjs
```

- 不设 `XIAO_LONG_XIA_CAPTCHA` 但 `HEADLESS=0` 时，会在登录处 **暂停**，你在浏览器里手输验证码后在 Playwright Inspector 里继续。
- `MENU_STEPS`、`fillForm()` 默认多为注释；要测菜单/查询页，先取消注释并改文案与选择器。

**录选择器（推荐）**：

```powershell
npx playwright codegen http://10.25.145.37:10003/
```

人工登录一遍，把生成的定位方式抄回 `automation-template.mjs`。

### C. 仅测技能文案（不写代码）

在 Cursor 或其它已挂载本技能目录的 Agent 里直接问：「按 SKILL.md，登录后进仓库 MMS 图形化页，查询区有哪些字段？」应能根据 `SKILL.md` / `reference.md` 答出结构说明（不代替真实点网页）。
