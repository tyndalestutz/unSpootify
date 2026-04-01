const { spawn } = require('child_process');
const path = require('path');

const sldlPath = path.join(__dirname, '../bin/sldl');

function runSldl({ username, password, folder, playlist, options = {} }, onData, onClose) {
    const args = [];

    if (username) args.push('--user', username);
    if (password) args.push('--pass', password);
    if (folder) args.push('-p', folder);
    if (playlist) args.push(playlist);

    // Add all other options
    for (const [key, value] of Object.entries(options)) {
        args.push(key);
        if (value !== true) args.push(value);
    }

    // Always use non-interactive fast mode
    args.push('--fast-search', '--no-incomplete-ext');

    const sldl = spawn(sldlPath, args);

    sldl.stdout.on('data', (data) => onData(data.toString()));
    sldl.stderr.on('data', (data) => onData(data.toString()));

    sldl.on('close', (code) => onClose(code));

    return sldl;
}

module.exports = runSldl;
