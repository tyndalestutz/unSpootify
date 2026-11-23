// server/server.js
import express from 'express';
import http from 'http';
import WebSocket from 'ws';
import path from 'path';
import { fileURLToPath } from 'url';
import { spotifyToCsv } from './spotifyToCsv.js';
import { runSldl } from './sldlRunner.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

let currentProcess = null;

wss.on('connection', ws => {
    ws.on('message', async message => {
        const { action, spotifyUrl, options } = JSON.parse(message);

        if (action === 'start') {
            try {
                ws.send('Loading Spotify playlist...');

                // 1️⃣ Convert Spotify URL → CSV
                const csvPath = await spotifyToCsv(spotifyUrl, path.join(__dirname, '../downloads'));
                ws.send(`Spotify playlist converted to CSV: ${csvPath}`);

                // 2️⃣ Run sldl with CSV
                currentProcess = runSldl(
                    csvPath,
                    options,
                    path.join(__dirname, '..'), // cwd
                    data => ws.send(data),
                    code => ws.send(`Process exited with code ${code}`)
                );

            } catch (err) {
                ws.send(`Error: ${err.message}`);
            }
        } else if (action === 'reset' && currentProcess) {
            currentProcess.kill();
            ws.send('Process terminated');
            currentProcess = null;
        }
    });
});

const PORT = 3000;
server.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));