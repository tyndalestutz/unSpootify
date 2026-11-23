// server/sldlRunner.js
import { spawn } from 'child_process';
import path from 'path';

// Run sldl with CSV input and options
export function runSldl(csvPath, options = {}, cwd, onData, onClose) {
    const args = [
        csvPath,
        '--input-type', 'csv',
        ...(options.concurrent ? ['--concurrent-downloads', options.concurrent] : []),
        ...(options.fastSearch ? ['--fast-search'] : [])
    ];

    const sldlPath = path.join(cwd, 'bin', 'sldl');

    const proc = spawn(sldlPath, args, { cwd });

    proc.stdout.on('data', data => onData(data.toString()));
    proc.stderr.on('data', data => onData(data.toString()));

    proc.on('close', code => onClose(code));

    return proc;
}