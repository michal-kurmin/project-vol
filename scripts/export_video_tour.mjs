/**
 * Optional Playwright + FFmpeg 1080p 60fps MP4 guided tour exporter.
 *
 * Usage:
 *   node scripts/export_video_tour.mjs
 *
 * Prerequisites:
 *   - Playwright installed in web/ or global (`npm i -D playwright`)
 *   - `ffmpeg` available on PATH
 */

import { spawn, execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const webDir = path.join(rootDir, 'web');
const outMp4 = path.join(rootDir, 'outputs', 'Project_Voltron_3D_Tour.mp4');
const tmpVideoDir = path.join(rootDir, 'outputs', '.tmp_tour_video');

function hasCommand(cmd) {
  try {
    execSync(`${cmd} -version`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

async function run() {
  if (!hasCommand('ffmpeg')) {
    console.error('[ERROR] ffmpeg is required on PATH to transcode WebM -> 1080p MP4.');
    process.exit(1);
  }

  let chromium;
  try {
    ({ chromium } = await import('playwright'));
  } catch {
    console.error('[ERROR] Playwright is not installed. Run: cd web && npm install -D playwright');
    process.exit(1);
  }

  fs.mkdirSync(tmpVideoDir, { recursive: true });
  const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  const server = spawn(npmCmd, ['run', 'dev', '--', '--port', '4173'], {
    cwd: webDir,
    stdio: 'pipe',
  });

  await new Promise((resolve) => setTimeout(resolve, 3000));

  try {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      recordVideo: { dir: tmpVideoDir, size: { width: 1920, height: 1080 } },
    });
    const page = await context.newPage();
    await page.goto('http://localhost:4173', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Trigger Guided Tour playback
    const tourBtn = page.getByRole('button', { name: /Play Guided Tour/i });
    await tourBtn.click();
    // 8 chapters (~42s total tour)
    await page.waitForTimeout(44000);

    const videoPath = await page.video().path();
    await context.close();
    await browser.close();

    execSync(
      `ffmpeg -y -i "${videoPath}" -c:v libx264 -r 60 -pix_fmt yuv420p -crf 18 "${outMp4}"`,
      { stdio: 'inherit' }
    );
    console.log(`Exported 1080p 60fps MP4 tour: ${outMp4}`);
  } finally {
    server.kill('SIGTERM');
    fs.rmSync(tmpVideoDir, { recursive: true, force: true });
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
