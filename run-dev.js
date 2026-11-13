const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const isWindows = process.platform === 'win32';
const rootDir = __dirname;
const backendDir = path.join(rootDir, 'backend');
const frontendDir = path.join(rootDir, 'frontend');

// ANSI colors
const RESET = '\x1b[0m';
const BOLD = '\x1b[1m';
const CYAN = '\x1b[36m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const RED = '\x1b[31m';
const GRAY = '\x1b[90m';

function log(prefix, color, message) {
  const lines = message.toString().split('\n');
  for (const line of lines) {
    if (line.trim().length > 0) {
      console.log(`${color}${BOLD}[${prefix}]${RESET} ${line}`);
    }
  }
}

function findPython() {
  const venvCandidates = isWindows ? [
    path.join(backendDir, '.venv', 'Scripts', 'python.exe'),
    path.join(backendDir, 'venv', 'Scripts', 'python.exe'),
    path.join(rootDir, '.venv', 'Scripts', 'python.exe'),
    path.join(rootDir, 'venv', 'Scripts', 'python.exe'),
  ] : [
    path.join(backendDir, '.venv', 'bin', 'python'),
    path.join(backendDir, 'venv', 'bin', 'python'),
    path.join(rootDir, '.venv', 'bin', 'python'),
    path.join(rootDir, 'venv', 'bin', 'python'),
  ];

  for (const candidate of venvCandidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return isWindows ? 'python' : 'python3';
}

function checkFrontendDeps() {
  const nodeModulesPath = path.join(frontendDir, 'node_modules');
  if (!fs.existsSync(nodeModulesPath)) {
    log('system', YELLOW, 'Frontend node_modules not found. Installing frontend dependencies...');
    const npmCmd = isWindows ? 'npm.cmd' : 'npm';
    execSync(`${npmCmd} install`, { cwd: frontendDir, stdio: 'inherit' });
    log('system', GREEN, 'Frontend dependencies installed successfully.');
  }
}

const processes = [];

function killProcess(proc) {
  if (!proc || !proc.pid) return;
  try {
    if (isWindows) {
      execSync(`taskkill /pid ${proc.pid} /T /F`, { stdio: 'ignore' });
    } else {
      process.kill(-proc.pid, 'SIGKILL');
    }
  } catch (e) {
    try {
      proc.kill('SIGKILL');
    } catch (_) {}
  }
}

function cleanup() {
  log('system', YELLOW, 'Shutting down services...');
  for (const p of processes) {
    killProcess(p);
  }
  process.exit(0);
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
process.on('SIGHUP', cleanup);

async function start() {
  console.log(`\n${BOLD}========================================${RESET}`);
  console.log(`${BOLD} Starting FixIt Application (Backend + Frontend)${RESET}`);
  console.log(`${BOLD}========================================\n${RESET}`);

  checkFrontendDeps();

  const pythonExec = findPython();
  log('system', GRAY, `Using Python: ${pythonExec}`);

  // 1. Start Backend (FastAPI / Uvicorn on port 8002)
  const backendArgs = ['-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '8002'];
  const backendProc = spawn(pythonExec, backendArgs, {
    cwd: backendDir,
    shell: isWindows,
    detached: !isWindows,
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  processes.push(backendProc);

  backendProc.stdout.on('data', (data) => log('backend', CYAN, data));
  backendProc.stderr.on('data', (data) => log('backend', CYAN, data));

  backendProc.on('error', (err) => {
    log('backend', RED, `Backend process error: ${err.message}`);
  });

  backendProc.on('exit', (code) => {
    if (code !== null && code !== 0) {
      log('backend', RED, `Backend exited with code ${code}`);
    }
  });

  // 2. Start Frontend (Vite on port 5173)
  const npmCmd = isWindows ? 'npm.cmd' : 'npm';
  const frontendProc = spawn(npmCmd, ['run', 'dev'], {
    cwd: frontendDir,
    shell: isWindows,
    detached: !isWindows,
    env: process.env
  });

  processes.push(frontendProc);

  frontendProc.stdout.on('data', (data) => log('frontend', GREEN, data));
  frontendProc.stderr.on('data', (data) => log('frontend', GREEN, data));

  frontendProc.on('error', (err) => {
    log('frontend', RED, `Frontend process error: ${err.message}`);
  });

  frontendProc.on('exit', (code) => {
    if (code !== null && code !== 0) {
      log('frontend', RED, `Frontend exited with code ${code}`);
    }
  });

  log('system', GREEN, 'Dev servers launched! Backend on http://127.0.0.1:8002 | Frontend on http://localhost:5175');
}

start();
