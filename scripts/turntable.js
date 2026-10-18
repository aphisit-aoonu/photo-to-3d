// node scripts/turntable.js <model.glb path relative to project> <out dir> [frames] [size] [radius e.g. "40%" for close-up] [target e.g. "auto 0.3m auto"]
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const [model, outDir, frames = 120, size = 1080, radius = 'auto', target = ''] = process.argv.slice(2);
const CHROME = path.join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe');

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--use-angle=d3d11', '--enable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({ width: +size, height: +size });
  await page.goto(`http://localhost:8765/render.html?m=${encodeURIComponent(model)}`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => window.ready);
  if (target) await page.evaluate((t) => { document.getElementById('mv').cameraTarget = t; }, target);
  for (let i = 0; i < +frames; i++) {
    const deg = (i * 360) / frames;
    await page.evaluate((d, r) => window.setAngle(d, 75, r), deg, radius);
    await page.screenshot({ path: path.join(outDir, `f${String(i).padStart(4, '0')}.png`), omitBackground: true });
  }
  await browser.close();
  console.log('done', frames, 'frames ->', outDir);
})();
