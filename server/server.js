const express = require('express');
const path = require('path');
const http = require('http');
const WebSocket = require('ws');
const runSldl = require('./sldlRunner');

const app = express();
const port = 3000;

app.use(express.static(path.join(__dirname, '../public')));
app.use(express.json());

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

let currentProcess = null;

wss.on('connection', (ws) => {
    ws.on('message', (msg) => {
        const { action, payload } = JSON.parse(msg);

        if (action === 'start') {
            currentProcess = runSldl(payload, 
                (data) => ws.send(data), 
                (code) => {
                    ws.send(`Process exited with code ${code}`);
                    currentProcess = null;
                }
            );
        } else if (action === 'reset' && currentProcess) {
            currentProcess.kill();
            ws.send('Process terminated');
            currentProcess = null;
        }
    });
});

server.listen(port, () => console.log(`Server running on http://localhost:${port}`));
