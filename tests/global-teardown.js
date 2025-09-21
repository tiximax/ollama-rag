import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { execSync } from 'node:child_process';

export default async function globalTeardown() {
  try {
    const pidFile = join(process.cwd(), 'tests', '.tmp', 'ollama.pid');
    if (existsSync(pidFile)) {
      const pidRaw = readFileSync(pidFile, 'utf-8').trim();
      const pid = parseInt(pidRaw, 10);
      if (!Number.isNaN(pid)) {
        try {
          process.kill(pid);
        } catch {
          try {
            execSync(`taskkill /PID ${pid} /T /F`);
          } catch {}
        }
      }
    }
  } catch {}
}
