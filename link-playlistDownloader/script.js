// Select elements
const usernameField = document.getElementById('username');
const passwordField = document.getElementById('password');
const folderPathField = document.getElementById('folderPath');
const playlistURLField = document.getElementById('playlistURL');
const mockTerminal = document.getElementById('mockTerminal');
const chooseFolderButton = document.getElementById('chooseFolderButton');

// Set initial terminal output
let baseCommand = "audiophile@unSpootify:~/sldl$ ./sldl";
let command = baseCommand;

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

// Update terminal in real-time when fields lose focus (on 'blur')
function updateCommand() {
    const username = usernameField.value ? ` --user ${usernameField.value}` : '';
    const password = passwordField.value ? ` --pass ${passwordField.value}` : '';
    const folderPath = folderPathField.value ? ` -p ${folderPathField.value}` : '';
    const playlistURL = playlistURLField.value ? ` ${playlistURLField.value}` : '';
    
    command = `${baseCommand}${username}${password}${folderPath}${playlistURL}`;
    mockTerminal.textContent = command;
    scrollToBottom();  // Ensure new lines stay at the bottom
    addBlinkingCursor();
}

// Event listeners for real-time updates
usernameField.addEventListener('blur', updateCommand);
passwordField.addEventListener('blur', updateCommand);
playlistURLField.addEventListener('blur', updateCommand);

// Scroll the mock terminal to the bottom as new lines are added
function scrollToBottom() {
    mockTerminal.scrollTop = mockTerminal.scrollHeight;
}

// Manual folder path entry (until Electron or native API is used)
chooseFolderButton.addEventListener('click', function () {
    const folderPath = prompt("Please manually enter the absolute path of your download folder:", "/home/yourusername/Music/");
    if (folderPath !== null) {
        folderPathField.value = folderPath;
        updateCommand();  // Update terminal with folder path
    }
});

// Initialize the terminal with a blinking cursor
addBlinkingCursor();

// Scroll event to ensure full scrollability in the mock terminal
mockTerminal.addEventListener('scroll', () => {
    mockTerminal.scrollTop = mockTerminal.scrollHeight;  // Ensure scrolling goes all the way down
});
