# 参考（OpenClaw + Playwright 兜底）

## 与本技能目录的路径

OpenClaw 解析技能时可用 `{baseDir}` 表示本仓库根目录（含 `SKILL.md` 的文件夹）。

## OpenClaw 浏览器

文档：<https://docs.openclaw.ai/tools/browser>

工作流：`navigate` → `snapshot` → `act(ref)` → 必要时循环。内网慢则调大超时（若配置支持）。

## 登录与图形验证码

- 验证码输入框：页面占位为 **「请输入验证码」**，优先 `getByPlaceholder('请输入验证码')`。
- 验证码图片：通常在输入框右侧；若需换图可点击图片区域（具体 DOM 以 `codegen` 为准）。
- **推荐策略（内网）**
  1. **人工读图**：每轮登录前用户看屏报 4 位数字，Agent 只负责填入并提交。
  2. **环境变量**：自动化脚本支持 `XIAO_LONG_XIA_CAPTCHA=xxxx`（勿提交到 git）。
  3. **headed + 暂停**：`HEADLESS=0` 且不设验证码环境变量时，脚本会 `page.pause()`，你在 DevTools 恢复前手输验证码。
- 若后端提供 **测试环境关闭验证码** 或 **固定测试码**，优先用该方式做 CI，而不是依赖 OCR 破解生产验证码。

## 侧栏菜单（登录后）

一级菜单（与界面文案一致，用于口述或 `clickText` 步骤）：

成本管理、应用集成平台、系统开发管理、工厂建模、工厂监控、采购管理、销售管理、出厂管理、财务管理、铁区管理、资源管理、质量管理、质量先期策划、智慧质量、生产合同管理、作业计划管理、物料管理。

**自动化建议**

1. 先点 **一级名称** 展开，再点 **子菜单** 文案（子项名称随权限/版本变化，以当前环境为准）。
2. OpenClaw：展开后务必 **重新 snapshot**，避免用过期的 ref。
3. Playwright：若 `getByRole` 不稳定，可用模板中的 `{ type: "clickText", text: "采购管理" }`；若匹配多项，改为 `selector` 或在脚本里改为 `.sidebar` 等作用域缩小范围。
4. 展开动画：两次点击之间可加 `await expect(page.getByText('子菜单名')).toBeVisible()` 或短 `waitForTimeout`（次选）。

### 示例路径：仓库管理(MMS) → 仓库图形化

层级（先保证上级已展开，再点下一级）：

1. **仓库管理(MMS)X**（一级文件夹；若界面文案无末尾 `X` 则以实际为准）
2. **仓库图形化**（二级文件夹）
3. **叶子菜单**（文档图标，任选其一进入页面）：

   - 全厂仓库分布图  
   - 仓库图形化显示_散料  
   - 仓库图形化显示_板坯（截图中为当前选中项）  
   - 仓库图形化显示_钢卷  
   - 仓库图形化显示_棒线  
   - 仓库图形化显示_立体  
   - 仓库图形化调度_板坯  
   - 仓库图形化调度_钢卷  
   - 仓库图形化执行_钢卷  
   - 仓库图形化执行_板坯  
   - 全厂仓库分布图元素（若被裁切，滚动侧栏后再点）

**Playwright `MENU_STEPS` 顺序示例**（与 `automation-template.mjs` 注释一致）：

```js
{ type: "clickText", text: "仓库管理(MMS)X" },
{ type: "clickText", text: "仓库图形化" },
{ type: "clickText", text: "仓库图形化显示_板坯" },
```

若 `getByText` 匹配到多处，请用 `codegen` 录一条 `selector` 步骤缩小到侧栏容器。

## Playwright 模板

编辑 `{baseDir}/scripts/automation-template.mjs` 中的 `SELECTORS`、`MENU_STEPS`、`fillForm()`。

`MENU_STEPS` 支持：`click`（`role`+`name`）、`clickText`（`text`）、`click`+`selector`。通用示例：

```js
// { type: "clickText", text: "采购管理" },
// { type: "clickText", text: "采购订单" },
```

仓库图形化示例见上文「示例路径」一节。

## 查询页 / 明细表（仓库图形化进入后的典型页）

### 查询条件区

| 字段 | 控件类型 | 自动化提示 |
|------|-----------|------------|
| 库区号 | 下拉 | 先点控件展开，再点选项文案；或用 `getByLabel` + 键盘/原生 select |
| 库业务类型 | 文本 | `getByLabel` / 相邻 input |
| 材料号 | 文本 | 同上 |
| 牌号(钢级) | 文本 | 标签可能带括号，以页面为准 |
| 合同号 | 文本 | 同上 |
| 机组代码 | 下拉 | 同库区号 |
| 事件发生时间 | 起止日期时间 | Element/Ant 常见为两个输入或 RangePicker；可尝试直接 `fill` 可见 input，失败则 `codegen` 录点击序列 |

填完后点击 **「F2查询」**；若按钮难定位，可试 `page.keyboard.press('F2')`（需页面已监听快捷键且焦点在主区域）。

### 详细信息显示区

表头（示例，以环境为准）：起始库区号、库区号、材料号、库业务类型、出入库时间、出入库区分、材料形态标志、合同号、材料实际厚度、材料实际宽度、材料实际长度。

断言：无数据时出现 **「无相关数据」**；有数据时等待表格行或网络空闲再读单元格。

### 其它控件

- **Excel 图标**：导出；仅在需要导出时再点，注意文件下载路径。
- **分页**：切页后再 `snapshot` 读数。

调试：`npx playwright codegen http://10.25.145.37:10003/`

安全：日志勿打印密码与验证码；截图勿提交 git。
