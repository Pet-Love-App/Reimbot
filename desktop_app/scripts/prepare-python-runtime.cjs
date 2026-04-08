const fs = require("node:fs");
const path = require("node:path");

const appRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(appRoot, "..");
const sourceVenv = path.join(repoRoot, ".venv");
const targetRuntime = path.join(appRoot, "python");

function fail(message) {
  console.error(`[prepare-python-runtime] ${message}`);
  process.exit(1);
}

if (!fs.existsSync(sourceVenv)) {
  fail(`未找到虚拟环境目录: ${sourceVenv}`);
}

const sourcePythonExe = path.join(sourceVenv, "Scripts", "python.exe");
if (!fs.existsSync(sourcePythonExe)) {
  fail(`未找到 Python 可执行文件: ${sourcePythonExe}`);
}

if (fs.existsSync(targetRuntime)) {
  fs.rmSync(targetRuntime, { recursive: true, force: true });
}

fs.cpSync(sourceVenv, targetRuntime, {
  recursive: true,
  force: true,
});

const targetPythonExe = path.join(targetRuntime, "Scripts", "python.exe");
if (!fs.existsSync(targetPythonExe)) {
  fail(`复制后缺少 Python 可执行文件: ${targetPythonExe}`);
}

console.log(`[prepare-python-runtime] runtime ready: ${targetRuntime}`);
