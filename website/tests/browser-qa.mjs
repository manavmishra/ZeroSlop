import assert from "node:assert/strict";
import { chromium } from "playwright-core";

const chromePath =
  process.env.CHROME_PATH ??
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const baseUrl = process.env.BASE_URL ?? "http://127.0.0.1:3002/";

const browser = await chromium.launch({ executablePath: chromePath, headless: true });

try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    permissions: ["clipboard-read", "clipboard-write"],
  });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  const response = await page.goto(baseUrl, { waitUntil: "networkidle" });
  assert.equal(response?.status(), 200);
  assert.equal(await page.locator("h1").textContent(), "Make AI writing sound like you.");

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
    main: Boolean(document.querySelector("main#main-content")),
  }));
  assert.equal(layout.main, true);
  assert.ok(layout.document <= layout.viewport, `horizontal overflow: ${JSON.stringify(layout)}`);

  const examples = page.locator("#examples");
  await examples.scrollIntoViewIfNeeded();
  const linkedInTab = examples.getByRole("tab", { name: "LinkedIn post" });
  const blogTab = examples.getByRole("tab", { name: "Blog intro" });
  const strategyTab = examples.getByRole("tab", { name: "Strategy document" });
  const threadTab = examples.getByRole("tab", { name: "X thread" });
  const slidesTab = examples.getByRole("tab", { name: "PowerPoint slide" });
  assert.equal(await linkedInTab.getAttribute("aria-selected"), "true");
  await blogTab.click();
  assert.equal(await blogTab.getAttribute("aria-selected"), "true");
  await strategyTab.press("ArrowRight");
  assert.equal(await threadTab.getAttribute("aria-selected"), "true");
  await slidesTab.click();
  await examples.getByRole("tabpanel").getByText("Shorten the sales cycle with AI").waitFor();
  assert.equal(await slidesTab.getAttribute("aria-selected"), "true");
  const slideOverflow = await examples.locator(".sample-slide").evaluateAll((slides) =>
    slides.map((slide) => ({ client: slide.clientHeight, scroll: slide.scrollHeight })),
  );
  assert.ok(
    slideOverflow.every(({ client, scroll }) => scroll <= client),
    `PowerPoint copy is clipped: ${JSON.stringify(slideOverflow)}`,
  );

  await page.getByRole("link", { name: "Install", exact: true }).first().click();
  assert.equal(await page.getByRole("list", { name: "Compatible agents" }).getByRole("listitem").count(), 7);
  await page.getByRole("button", { name: "Copy the Zero Slop install command" }).click();
  await page.getByRole("button", { name: "Copy the Zero Slop install command" }).getByText("Copied").waitFor();
  assert.equal(
    await page.evaluate(() => navigator.clipboard.readText()),
    "npx skills add manavmishra/ZeroSlop --global",
  );

  const faq = page.getByText("Does the scorer send my writing anywhere?");
  await faq.click();
  assert.equal(await faq.locator("xpath=ancestor::details").getAttribute("open"), "");
  const skipBottom = await page.locator(".skip-link").evaluate((element) =>
    element.getBoundingClientRect().bottom,
  );
  assert.ok(skipBottom < 0, `skip link should stay off-canvas until focused: ${skipBottom}`);

  await page.screenshot({ path: ".quality/mobile-final.png", fullPage: true });
  assert.deepEqual(errors, []);
  await context.close();

  const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const desktopPage = await desktop.newPage();
  await desktopPage.goto(baseUrl, { waitUntil: "networkidle" });
  const lightCanvas = await desktopPage.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await desktopPage.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await desktopPage.reload({ waitUntil: "networkidle" });
  const darkCanvas = await desktopPage.evaluate(() => getComputedStyle(document.body).backgroundColor);
  assert.notEqual(lightCanvas, darkCanvas);
  await desktopPage.locator("#proof").scrollIntoViewIfNeeded();
  await desktopPage.waitForFunction(() =>
    [...document.images].every((image) => image.complete),
  );
  await desktopPage.locator("#proof").screenshot({ path: ".quality/proof-final.png" });
  await desktopPage.screenshot({ path: ".quality/desktop-final.png", fullPage: true });
  await desktop.close();

  console.log("Browser QA passed: examples, mobile flow, clipboard, FAQ, overflow, themes, reduced motion, and console.");
} finally {
  await browser.close();
}
