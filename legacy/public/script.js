// script.js
const usernameField = document.getElementById('username');
const passwordField = document.getElementById('password');
const folderPathField = document.getElementById('folderPath');
const playlistURLField = document.getElementById('playlistURL');
const basicOptionsTable = document.getElementById('basicOptionsTable');
const advancedOptionsTable = document.getElementById('advancedOptionsTable');
const mockTerminal = document.getElementById('mockTerminal');
const downloadButton = document.getElementById('downloadButton');

let options = {};
let isRunning = false;

// WebSocket connection
const socket = new WebSocket('ws://localhost:3000');

socket.addEventListener('message', (event) => {
    mockTerminal.textContent += '\n' + event.data;
    scrollToBottom();
});

// Blinking cursor
function addBlinkingCursor() {
    const cursor = document.createElement('span');
    cursor.id = 'blinkingCursor';
    cursor.textContent = '_';
    mockTerminal.appendChild(cursor);
    setInterval(() => {
        cursor.style.visibility = cursor.style.visibility === 'hidden' ? 'visible' : 'hidden';
    }, 500);
}

// Option row creator (unchanged)
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
            if (input.value) options[optionData.name] = `${optionData.name} ${input.value}`;
            else delete options[optionData.name];
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
            if (button.classList.contains('on')) options[optionData.name] = input ? `${optionData.name} ${input.value}` : optionData.name;
            else delete options[optionData.name];
            updateCommand();
        }
    });
    toggleButton.appendChild(button);
    row.appendChild(toggleButton);

    container.appendChild(row);
}

// Fill options (same as before)
const basicOptionsData = [
    { name: "-a", description: "Download a folder", requiresInput: false },
    { name: "--fast-search", description: "Download preferred files immediately", requiresInput: false },
    { name: "-d", description: "Try harder to find tracks", requiresInput: false },
];

basicOptionsData.forEach(option => createOptionRow(option, basicOptionsTable));

const advancedOptionsData = [
    { name: "-n", description: "Download first n tracks", requiresInput: true },
    { name: "-o", description: "Skip first n tracks", requiresInput: true },
    { name: "--no-progress", description: "Disable progress bars", requiresInput: false },
];

advancedOptionsData.forEach(option => createOptionRow(option, advancedOptionsTable));

function updateCommand() {
    const username = usernameField.value ? `--user ${usernameField.value}` : '';
    const password = passwordField.value ? `--pass ${passwordField.value}` : '';
    const folderPath = folderPathField.value ? `-p ${folderPathField.value}` : '';
    const playlistURL = playlistURLField.value ? playlistURLField.value : '';

    const commandOptions = `${username} ${password} ${folderPath} ${Object.values(options).join(' ')}`;

    mockTerminal.textContent = `audiophile@unSpootify:~/sldl$ ./sldl ${commandOptions} ${playlistURL}`;
    scrollToBottom();
    addBlinkingCursor();
}

function scrollToBottom() {
    mockTerminal.scrollTop = mockTerminal.scrollHeight;
}

// Download button event
downloadButton.addEventListener('click', () => {
    if (!isRunning) {
        const username = usernameField.value ? `--user ${usernameField.value}` : '';
        const password = passwordField.value ? `--pass ${passwordField.value}` : '';
        const folderPath = folderPathField.value ? `-p ${folderPathField.value}` : '';
        const playlistURL = playlistURLField.value ? playlistURLField.value : '';

        const commandOptions = `${username} ${password} ${folderPath} ${Object.values(options).join(' ')}`;

        // Send WebSocket with spotifyUrl
        socket.send(JSON.stringify({
            action: 'start',
            command: commandOptions,
            spotifyUrl: playlistURL
        }));

        isRunning = true;
        downloadButton.textContent = "Reset";
    } else {
        socket.send(JSON.stringify({ action: 'reset' }));
        isRunning = false;
        downloadButton.textContent = "Download";
        mockTerminal.textContent = '';
    }
});

document.getElementById('toggleAdvancedOptions').addEventListener('click', () => {
    const advancedOptions = document.getElementById('advancedOptionsContainer');
    advancedOptions.classList.toggle('hidden');
    const button = document.getElementById('toggleAdvancedOptions');
    button.textContent = advancedOptions.classList.contains('hidden') ? "Show Advanced Options" : "Hide Advanced Options";
});

usernameField.addEventListener('blur', updateCommand);
passwordField.addEventListener('blur', updateCommand);
playlistURLField.addEventListener('blur', updateCommand);
folderPathField.addEventListener('blur', updateCommand);

addBlinkingCursor();