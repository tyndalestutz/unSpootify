// Select elements
const usernameField = document.getElementById('username');
const passwordField = document.getElementById('password');
const folderPathField = document.getElementById('folderPath');
const playlistURLField = document.getElementById('playlistURL');
const basicOptionsTable = document.getElementById('basicOptionsTable');
const advancedOptionsTable = document.getElementById('advancedOptionsTable');
const mockTerminal = document.getElementById('mockTerminal');
const downloadButton = document.getElementById('downloadButton');

// Command-related variables
let baseCommand = "audiophile@unSpootify:~/sldl$ ./sldl";
let options = {};
let isRunning = false; // Track if a command is running

// Initialize WebSocket connection
const socket = new WebSocket('ws://localhost:3000');

// Listen for messages (output from the command)
socket.addEventListener('message', (event) => {
    mockTerminal.textContent += '\n' + event.data;
    scrollToBottom();
});

// Blinking cursor effect
function addBlinkingCursor() {
    const cursor = document.createElement('span');
    cursor.id = 'blinkingCursor';
    cursor.textContent = '_';
    mockTerminal.appendChild(cursor);
    setInterval(() => {
        cursor.style.visibility = cursor.style.visibility === 'hidden' ? 'visible' : 'hidden';
    }, 500);
}

// Dynamically create option rows
function createOptionRow(optionData, container) {
    const row = document.createElement('tr');

    const optionName = document.createElement('td');
    optionName.textContent = optionData.name;
    row.appendChild(optionName);

    const inputField = document.createElement('td');
    let input = null;
    if (optionData.requiresInput) {
        input = document.createElement('input');
        input.type = 'text';
        input.className = 'option-input';
        input.addEventListener('blur', () => {
            if (input.value) {
                options[optionData.name] = `${optionData.name} ${input.value}`;
            } else {
                delete options[optionData.name];
            }
            updateCommand();
        });
        inputField.appendChild(input);
    }
    row.appendChild(inputField);

    const description = document.createElement('td');
    description.textContent = optionData.description;
    row.appendChild(description);

    const toggleButton = document.createElement('td');
    const button = document.createElement('button');
    button.textContent = "Off";
    button.classList.add('option-button');
    button.addEventListener('click', () => {
        button.classList.toggle('on');
        button.textContent = button.classList.contains('on') ? 'On' : 'Off';

        if (!optionData.requiresInput || input.value) {
            if (button.classList.contains('on')) {
                options[optionData.name] = input ? `${optionData.name} ${input.value}` : optionData.name;
            } else {
                delete options[optionData.name];
            }
            updateCommand();
        }
    });
    toggleButton.appendChild(button);
    row.appendChild(toggleButton);

    container.appendChild(row);
}

// Populate the tables with the options
const basicOptionsData = [
    { name: "-a", description: "Download a folder", requiresInput: false },
    { name: "--concurrent-downloads", description: "Max concurrent downloads", requiresInput: true },
    { name: "--fast-search", description: "Download as soon as a preferred file is found", requiresInput: false },
    { name: "-d", description: "Desperate: Try harder to find tracks", requiresInput: false }
];

const advancedOptionsData = [
    { name: "--input-type", description: "[csv|youtube|spotify|bandcamp|string|list]", requiresInput: true },
    { name: "--name-format", description: "Name format for tracks", requiresInput: true },
    { name: "-n", description: "Download the first n tracks of a playlist", requiresInput: true },
    { name: "-o", description: "Skip a specified number of tracks", requiresInput: true },
    { name: "-r", description: "Download tracks in reverse order", requiresInput: false },
    { name: "-c", description: "Set config file location", requiresInput: true },
    { name: "--profile", description: "Configuration profile(s) to use", requiresInput: true },
    { name: "--write-playlist", description: "Create an m3u playlist file", requiresInput: false },
    { name: "--playlist-path", description: "Override default path for m3u file", requiresInput: true },
    { name: "--no-skip-existing", description: "Do not skip downloaded tracks", requiresInput: false },
    { name: "--no-write-index", description: "Do not create a file index", requiresInput: false },
    { name: "--index-path", description: "Override default path for index file", requiresInput: true },
    { name: "--skip-check-cond", description: "Check file conditions when skipping", requiresInput: false },
    { name: "--skip-check-pref-cond", description: "Check preferred file conditions", requiresInput: false },
    { name: "--skip-music-dir", description: "Skip downloading tracks in a music library", requiresInput: true },
    { name: "--skip-not-found", description: "Skip tracks not found in last run", requiresInput: false },
    { name: "--listen-port", description: "Set port for incoming connections", requiresInput: true },
    { name: "--on-complete", description: "Run command on file completion", requiresInput: true },
    { name: "--print", description: "Print tracks or search results", requiresInput: true },
    { name: "--no-progress", description: "Disable progress bars", requiresInput: false },
    { name: "--debug", description: "Print extra debug information", requiresInput: false },
    { name: "--remove-ft", description: "Remove 'feat.' from searches", requiresInput: false },
    { name: "--no-remove-special-chars", description: "Do not remove special characters", requiresInput: false },
    { name: "--remove-brackets", description: "Remove brackets from searches", requiresInput: false },
    { name: "--regex", description: "Remove or replace a regex pattern", requiresInput: true },
    { name: "--yt-dlp", description: "Use yt-dlp for downloading tracks", requiresInput: false },
    { name: "--yt-dlp-argument", description: "Arguments for yt-dlp", requiresInput: true }
];

// Fill basic and advanced option tables
basicOptionsData.forEach(option => createOptionRow(option, basicOptionsTable));
advancedOptionsData.forEach(option => createOptionRow(option, advancedOptionsTable));

// Modify the command update function to send a clean command
function updateCommand() {
    const username = usernameField.value ? `--user ${usernameField.value}` : '';
    const password = passwordField.value ? `--pass ${passwordField.value}` : '';
    const folderPath = folderPathField.value ? `-p ${folderPathField.value}` : '';
    const playlistURL = playlistURLField.value ? `${playlistURLField.value}` : '';

    const commandOptions = `${username} ${password} ${folderPath} ${playlistURL} ${Object.values(options).join(' ')}`;

    // Display with the prompt for UI purposes
    mockTerminal.textContent = `audiophile@unSpootify:~/sldl$ ./sldl ${commandOptions}`;
    scrollToBottom();
    addBlinkingCursor();
}

// Scroll the mock terminal to the bottom as new lines are added
function scrollToBottom() {
    mockTerminal.scrollTop = mockTerminal.scrollHeight;
}

// Event listener for the Download button
downloadButton.addEventListener('click', () => {
    if (!isRunning) {
        // Start command if not already running
        const username = usernameField.value ? `--user ${usernameField.value}` : '';
        const password = passwordField.value ? `--pass ${passwordField.value}` : '';
        const folderPath = folderPathField.value ? `-p ${folderPathField.value}` : '';
        const playlistURL = playlistURLField.value ? `${playlistURLField.value}` : '';

        const commandOptions = `${username} ${password} ${folderPath} ${playlistURL} ${Object.values(options).join(' ')}`;

        // Send the command to the WebSocket server
        socket.send(JSON.stringify({ command: commandOptions, action: 'start' }));
        isRunning = true;

        // Change button text to Reset
        downloadButton.textContent = "Reset";
    } else {
        // If running, reset the current process
        socket.send(JSON.stringify({ action: 'reset' }));
        isRunning = false;

        // Reset UI elements
        downloadButton.textContent = "Download";
        mockTerminal.textContent = '';
    }
});

// Toggle advanced options visibility
document.getElementById('toggleAdvancedOptions').addEventListener('click', () => {
    const advancedOptions = document.getElementById('advancedOptionsContainer');
    advancedOptions.classList.toggle('hidden');
    const button = document.getElementById('toggleAdvancedOptions');
    button.textContent = advancedOptions.classList.contains('hidden') ? "Show Advanced Options" : "Hide Advanced Options";
});

// Event listeners for real-time updates
usernameField.addEventListener('blur', updateCommand);
passwordField.addEventListener('blur', updateCommand);
playlistURLField.addEventListener('blur', updateCommand);
folderPathField.addEventListener('blur', updateCommand);

// Initialize the terminal with a blinking cursor
addBlinkingCursor();
