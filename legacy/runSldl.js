const { spawn } = require('child_process');
const path = require('path');

const sldlPath = path.join(__dirname, 'bin', 'sldl');
const downloadsPath = path.join(__dirname, 'downloads');

// Replace with your Soulseek account
const USER = "YOUR_USER";
const PASS = "YOUR_PASS";

// Example input
const albumQuery = "Daft Punk - Discovery";

// Spawn sldl process in non-interactive mode
const args = [
  albumQuery,
  '--user', USER,
  '--pass', PASS,
  '-p', downloadsPath,
  '--fast-search',       // auto-download first match
  '--no-skip-existing',  // optional: don't skip anything already downloaded
  '--no-incomplete-ext'  // optional: final filenames, no .incomplete
];

const sldl = spawn(sldlPath, args);

sldl.stdout.on('data', (data) => {
  console.log(`[sldl]: ${data}`);
});

sldl.stderr.on('data', (data) => {
  console.error(`[error]: ${data}`);
});

sldl.on('close', (code) => {
  console.log(`sldl exited with code ${code}`);
});
