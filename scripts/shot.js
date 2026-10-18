// node scripts/shot.js <url> <out.png> [width] [height] [waitMs]
const puppeteer = require('puppeteer-core');
const path = require('path');

const [url, out, w = 1440, h = 900, wait = 4000] = process.argv.slice(2);
const CHROME = path.join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe');

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--use-angle=d3d11', '--enable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({ width: +w, height: +h, deviceScaleFactor: 1 });
  await page.goto(url, { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, +wait));
  await page.screenshot({ path: out });
  await browser.close();
})();
