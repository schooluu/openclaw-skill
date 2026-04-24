/**
 * 无 OpenClaw browser 工具时的兜底：Playwright 模板。
 * 登录页含：账号、密码、图形验证码（占位「请输入验证码」）、「登录」按钮。
 * 运行：XIAO_LONG_XIA_USER / XIAO_LONG_XIA_PASS；验证码见下方 CAPTCHA 说明。
 */
import { chromium, expect } from "playwright";

const BASE_URL = process.env.XIAO_LONG_XIA_BASE_URL || "http://10.25.145.37:10003/";
const USER = process.env.XIAO_LONG_XIA_USER || "";
const PASS = process.env.XIAO_LONG_XIA_PASS || "";
/** 当前轮图形验证码明文；不要写进仓库 */
const CAPTCHA = process.env.XIAO_LONG_XIA_CAPTCHA || "";
const HEADLESS = process.env.HEADLESS !== "0";

/** 按实际 DOM 微调；验证码框占位为「请输入验证码」，账号为另一格 text */
const SELECTORS = {
  user: 'input[type="text"]:not([placeholder*="验证码"])',
  pass: 'input[type="password"]',
  captchaPlaceholder: "请输入验证码",
  submit: 'button:has-text("登录"), button[type="submit"]',
};

async function login(page) {
  if (!USER || !PASS) {
    throw new Error("请设置 XIAO_LONG_XIA_USER 与 XIAO_LONG_XIA_PASS");
  }
  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

  const userInput = page.locator(SELECTORS.user).first();
  await userInput.fill(USER);
  await page.locator(SELECTORS.pass).first().fill(PASS);

  const captchaBox = page.getByPlaceholder(SELECTORS.captchaPlaceholder);
  await expect(captchaBox).toBeVisible({ timeout: 15000 });

  if (CAPTCHA) {
    await captchaBox.fill(CAPTCHA);
  } else if (!HEADLESS) {
    // 有界面时暂停，便于肉眼读图后手输验证码
    console.log("未设置 XIAO_LONG_XIA_CAPTCHA：请在浏览器中输入验证码，然后在 Playwright Inspector 中继续。");
    await page.pause();
  } else {
    throw new Error(
      "headless 模式必须设置 XIAO_LONG_XIA_CAPTCHA，或改用 HEADLESS=0 配合 page.pause() 手输验证码",
    );
  }

  await page.locator(SELECTORS.submit).first().click();
  await page.waitForLoadState("networkidle").catch(() => {});
}

/**
 * 登录后左侧深蓝菜单：先点一级展开（右侧有▼），再点子菜单。
 * @type {Array<
 *   | { type: "click"; role: string; name: string }
 *   | { type: "click"; selector: string }
 *   | { type: "clickText"; text: string; exact?: boolean }
 * >}
 */
const MENU_STEPS = [
  // 仓库 MMS → 仓库图形化 → 叶子页（按需取消注释；一级名称以页面为准，可能无末尾 X）
  // { type: "clickText", text: "仓库管理(MMS)X" },
  // { type: "clickText", text: "仓库图形化" },
  // { type: "clickText", text: "仓库图形化显示_板坯" },
  // 其他叶子：全厂仓库分布图、仓库图形化显示_散料、仓库图形化显示_钢卷、仓库图形化显示_棒线、
  // 仓库图形化显示_立体、仓库图形化调度_板坯、仓库图形化调度_钢卷、仓库图形化执行_钢卷、
  // 仓库图形化执行_板坯、全厂仓库分布图元素
];

async function runMenu(page) {
  for (const step of MENU_STEPS) {
    if (step.type === "click" && "role" in step && step.role && "name" in step && step.name) {
      await page.getByRole(step.role, { name: step.name }).click();
    } else if (step.type === "click" && "selector" in step && step.selector) {
      await page.locator(step.selector).click();
    } else if (step.type === "clickText" && "text" in step && step.text) {
      const exact = step.exact !== false;
      await page.getByText(step.text, { exact }).first().click();
    }
  }
}

async function fillForm(page) {
  // --- 进入「查询条件 + 详细信息显示」类页面后（见 SKILL / reference）---
  // 下列为占位示例：请用 codegen 对照真实 DOM 调整 label / role。
  // const q = process.env;
  // if (q.QUERY_MATERIAL_NO) await page.getByLabel("材料号").fill(q.QUERY_MATERIAL_NO);
  // if (q.QUERY_CONTRACT_NO) await page.getByLabel("合同号").fill(q.QUERY_CONTRACT_NO);
  // 下拉：库区号 / 机组代码 — 先点击再选 getByRole("option", { name: "..." })
  // 时间范围：优先点选日期控件；或对环境变量解析后填入可见的起止 input
  // await page.getByRole("button", { name: /F2查询/ }).click();
  // await page.keyboard.press("F2").catch(() => {});
  // await expect(page.getByText("无相关数据").or(page.locator("table tbody tr"))).toBeVisible({ timeout: 30000 });
}

async function main() {
  const browser = await chromium.launch({ headless: HEADLESS });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(60000);

  try {
    await login(page);
    await runMenu(page);
    await fillForm(page);
    await expect(page.locator("body")).toBeVisible();
  } catch (e) {
    await page.screenshot({ path: "openclaw-fallback-error.png", fullPage: true }).catch(() => {});
    throw e;
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
