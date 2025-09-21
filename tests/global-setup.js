import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const PID_DIR = join(process.cwd(), 'tests', '.tmp');
const PID_FILE = join(PID_DIR, 'ollama.pid');

async function isOllamaUp() {
  try {
    const res = await fetch('http://127.0.0.1:11434/api/tags');
    return res.ok;
  } catch {
    return false;
  }
}

export default async function globalSetup() {
  const up = await isOllamaUp();
  if (!up) {
    console.log('[globalSetup] Starting ollama serve...');
    const child = spawn('ollama', ['serve'], {
      stdio: 'ignore',
      detached: true
    });
    child.unref();

    mkdirSync(PID_DIR, { recursive: true });
    writeFileSync(PID_FILE, String(child.pid));

    const start = Date.now();
    while (!(await isOllamaUp())) {
      if (Date.now() - start > 60_000) {
        throw new Error('Ollama did not start within 60s');
      }
      await new Promise(r => setTimeout(r, 1000));
    }
    console.log('[globalSetup] Ollama is ready.');
  } else {
    console.log('[globalSetup] Ollama already running.');
  }
}
