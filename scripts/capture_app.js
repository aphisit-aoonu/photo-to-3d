// Frame-by-frame capture of the real web app for the video, driven through its own functions.
// The build step (~1 min on Hugging Face) is shown shortened; the model is the app's real output for that job.
// node scripts/capture_app.js <jobId> <outDir>
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const [job, outDir] = process.argv.slice(2);
const CHROME = path.join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe');

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--use-angle=d3d11', '--enable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 980 });
  await page.goto('http://localhost:8770/', { waitUntil: 'networkidle0' });
  const photos = (await (await fetch(`http://localhost:8770/api/jobs/${job}`)).json()).photos;
  let n = 0;
  const shot = async (k = 1) => {
    for (let i = 0; i < k; i++) await page.screenshot({ path: path.join(outDir, `f${String(n++).padStart(4, '0')}.png`) });
  };
  await page.evaluate(() => { document.getElementById('mv').autoRotate = false; });
  await shot(12);
  for (let i = 1; i <= photos.length; i++) {
    await page.evaluate((p) => {
      showThumbs(p);
      document.querySelectorAll('#thumbs img').forEach((im) => { im.style.animation = 'none'; });
      document.getElementById('build').disabled = false;
    }, photos.slice(0, i));
    await new Promise((r) => setTimeout(r, 120));
    await shot(4);
  }
  await page.evaluate(() => { document.getElementById('build').disabled = true; setStatus('Building the 3D model', true); });
  for (let i = 0; i < 30; i++) { await new Promise((r) => setTimeout(r, 40)); await shot(); }
  await page.evaluate((j) => new Promise((res) => {
    const mv = document.getElementById('mv');
    mv.addEventListener('load', res, { once: true });
    showModel(j);
    setStatus(`Done · ${document.querySelectorAll('#thumbs img').length} photos`, false);
  }), job);
  for (let i = 0; i < 84; i++) {
    await page.evaluate((d) => new Promise((res) => {
      const mv = document.getElementById('mv');
      mv.cameraOrbit = `${d}deg 75deg auto`;
      mv.jumpCameraToGoal();
      requestAnimationFrame(() => requestAnimationFrame(res));
    }), -50 + i * 1.2);
    await shot();
  }
  await browser.close();
  console.log('frames', n);
})();
