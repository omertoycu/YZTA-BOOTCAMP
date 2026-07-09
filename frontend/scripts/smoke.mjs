// Frontend görsel smoke testi: verilen route'ları headless Chromium'da açar,
// ekran görüntüsü alır, konsol/page hatalarını raporlar.
//
// Kullanım (frontend/ içinden, dev server ayaktayken):
//   node scripts/smoke.mjs                    # varsayılan: / ve /login
//   node scripts/smoke.mjs / /login /dashboard
//
// Env:
//   SMOKE_BASE   hedef origin (varsayılan http://localhost:3000)
//   SMOKE_OUT    ekran görüntüsü dizini (varsayılan ./smoke-shots)
//   SMOKE_TOKEN  set edilirse localStorage'a portfoyai_token olarak yazılır —
//                korumalı sayfalar (/dashboard, /listings...) böyle gezilir.
//   SMOKE_VIEWPORT  "390x844" gibi — mobil görünüm doğrulaması için
//                   (varsayılan 1440x900).
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const BASE = process.env.SMOKE_BASE || "http://localhost:3000";
const OUT = process.env.SMOKE_OUT || "./smoke-shots";
const routes = process.argv.slice(2).length ? process.argv.slice(2) : ["/", "/login"];

mkdirSync(OUT, { recursive: true });

const [vw, vh] = (process.env.SMOKE_VIEWPORT || "1440x900").split("x").map(Number);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: vw, height: vh } });

const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(`[console] ${m.text()}`));
page.on("pageerror", (e) => errors.push(`[pageerror] ${e.message}`));

if (process.env.SMOKE_TOKEN) {
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate((t) => localStorage.setItem("portfoyai_token", t), process.env.SMOKE_TOKEN);
}

const results = [];
for (const route of routes) {
  const name = route === "/" ? "root" : route.replace(/^\//, "").replace(/[\/\[\]]/g, "_");
  const file = join(OUT, `${name}.png`);
  try {
    await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(600); // animasyonlar otursun
    await page.screenshot({ path: file });
    results.push({ route, ok: true, screenshot: file });
  } catch (err) {
    results.push({ route, ok: false, error: String(err) });
  }
}

await browser.close();

console.log(JSON.stringify({ base: BASE, results, consoleErrors: errors }, null, 2));
if (errors.length || results.some((r) => !r.ok)) process.exitCode = 1;
