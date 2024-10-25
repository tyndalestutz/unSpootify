const express = require('express');
const { exec } = require('child_process');
const cors = require('cors');
const path = require('path');
const app = express();
const port = 3000;

// Define paths
const publicDirectory = path.join(__dirname, 'public'); // Updated to reference public in the same directory
const sldlDirectory = path.join(__dirname, '../slsk-batchdl/slsk-batchdl/bin/Release/net6.0/linux-x64/publish'); // Directory for sldl

// Serve static files from the public directory
app.use(express.static(publicDirectory));
app.use(express.json());
app.use(cors());

// POST route for executing the command
app.post('/execute-command', (req, res) => {
    const { command } = req.body;

    // Prepend './sldl' to the command to execute it correctly
    const cleanCommand = `./sldl ${command.trim()}`;

    // Run the command in the specified working directory
    exec(cleanCommand, { cwd: sldlDirectory }, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error: ${error.message}`);
            return res.status(500).send(`Error: ${error.message}`);
        }
        if (stderr) {
            console.error(`Stderr: ${stderr}`);
            return res.status(500).send(`Stderr: ${stderr}`);
        }
        console.log(`Stdout: ${stdout}`);
        res.send(`Output: ${stdout}`);
    });
});

// Start the server
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
