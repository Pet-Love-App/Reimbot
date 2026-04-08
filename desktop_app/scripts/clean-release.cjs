const fs = require("node:fs");
const path = require("node:path");
const { execSync } = require("node:child_process");

const appRoot = path.resolve(__dirname, "..");
const releaseDir = path.join(appRoot, "release");

function tryTaskKill(imageName) {
  try {
    execSync(`taskkill /F /IM "${imageName}"`, { stdio: "ignore" });
  } catch {
    // Ignore: process may not exist.
  }
}

function removeDir(target) {
  if (!fs.existsSync(target)) {
    return;
  }
  fs.rmSync(target, {
    recursive: true,
    force: true,
    maxRetries: 8,
    retryDelay: 250,
  });
}

tryTaskKill("Finance Agent.exe");
tryTaskKill("electron.exe");
removeDir(releaseDir);
console.log(`[clean-release] cleaned: ${releaseDir}`);
