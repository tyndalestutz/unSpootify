const express = require('express');
const { spawn } = require('child_process');
const cors = require('cors');
const path = require('path');
const http = require('http');
const WebSocket = require('ws');

const app = express();
const port = 3000;
const publicDirectory = path.join(__dirname, 'public');
const sldlDirectory = path.join(__dirname, '../slsk-batchdl/slsk-batchdl/bin/Release/net6.0/linux-x64/publish');

app.use(express.static(publicDirectory));
app.use(express.json());
app.use(cors());

const server = http.createServer(app);

// Create a WebSocket server for real-time output
const wss = new WebSocket.Server({ server });

let currentProcess = null;

wss.on('connection', (ws) => {
    ws.on('message', (message) => {
        const { command, action } = JSON.parse(message);

        if (action === 'start') {
            // Run the command using spawn for real-time output
            currentProcess = spawn('./sldl', command.split(' '), { cwd: sldlDirectory });

            currentProcess.stdout.on('data', (data) => {
                ws.send(data.toString());
            });

            currentProcess.stderr.on('data', (data) => {
                ws.send(data.toString());
            });

            currentProcess.on('close', (code) => {
                ws.send(`Process exited with code ${code}`);
                currentProcess = null;
            });
        } else if (action === 'reset' && currentProcess) {
            // If reset is triggered, kill the running process
            currentProcess.kill();
            ws.send('Process terminated');
            currentProcess = null;
        }
    });
});

// Start the server
server.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
