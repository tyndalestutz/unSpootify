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

const socket = new WebSocket('ws://localhost:3000');

socket.addEventListener('message', (event) => {
    mockTerminal.textContent += '\n' + event.data;
    scrollToBottom();
});

function scrollToBottom() {
    mockTerminal.scrollTop = mockTerminal.scrollHeight;
}

function addBlinkingCursor() {
    const cursor = document.createElement('span');
    cursor.id = 'blinkingCursor';
    cursor.textContent = '_';
    mockTerminal.appendChild(cursor);
    setInterval(() => {
        cursor.style.visibility = cursor.style.visibility === 'hidden' ? 'visible' : 'hidden';
    }, 500);
}

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
            if (input.value) options[optionData.name] = input.value || true;
            else delete options[optionData.name];
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
        if (button.classList.contains('on')) options[optionData.name] = input ? input.value || true : true;
        else delete options[optionData.name];
    });
    toggleButton.appendChild(button);
    row.appendChild(toggleButton);

    container.appendChild(row);
}

const basicOptionsData = [
    { name: "-a", description: "Download a folder", requiresInput: false },
    { name: "--concurrent-downloads", description: "Max concurrent downloads", requiresInput: true },
    { name: "--fast-search", description: "Download as soon as preferred file is found", requiresInput: false },
    { name: "-d", description: "Desperate: try harder to find tracks", requiresInput: false }
];

const advancedOptionsData = [
    { name: "--input-type", description: "[csv|youtube|spotify|bandcamp|string|list]", requiresInput: true },
    { name: "--name-format", description: "Name format for tracks", requiresInput: true },
    { name: "-n", description: "Download the first n tracks of a playlist", requiresInput: true },
    { name: "-o", description: "Skip a specified number of tracks", requiresInput: true },
    { name: "-r", description: "Download tracks in reverse order", requiresInput: false },
    { name: "--profile", description: "Configuration profile(s) to use", requiresInput: true }
];

basicOptionsData.forEach(o => createOptionRow(o, basicOptionsTable));
advancedOptionsData.forEach(o => createOptionRow(o, advancedOptionsTable));

downloadButton.addEventListener('click', () => {
    if (!isRunning) {
        const payload = {
            username: usernameField.value,
            password: passwordField.value,
            folder: folderPathField.value,
            playlist: playlistURLField.value,
            options
        };
        socket.send(JSON.stringify({ action: 'start', payload }));
        isRunning = true;
        downloadButton.textContent = "Reset";
        mockTerminal.textContent = '';
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

addBlinkingCursor();
