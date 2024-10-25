let currentSort = 'date'; 
let selectedCount = 0; 
let selectedMode = 'song'; 

let isDragging = false;
let offsetX, offsetY;
const downloadManager = document.getElementById('downloadManager');
downloadManager.addEventListener('mousedown', function (e) {
    isDragging = true;
    offsetX = e.clientX - downloadManager.offsetLeft;
    offsetY = e.clientY - downloadManager.offsetTop;
});
document.addEventListener('mousemove', function (e) {
    if (isDragging) {
        downloadManager.style.left = (e.clientX - offsetX) + 'px';
        downloadManager.style.top = (e.clientY - offsetY) + 'px';
    }
});
document.addEventListener('mouseup', function () {
    isDragging = false;
});

function loadPlaylists(sortBy = 'date') {
    fetch('Playlist1.json')
        .then(response => response.json())
        .then(data => {
            let playlists = data.playlists;

            if (sortBy === 'title') {
                playlists.sort((a, b) => a.name.localeCompare(b.name));
            } else if (sortBy === 'date') {
                playlists.sort((a, b) => new Date(b.lastModifiedDate) - new Date(a.lastModifiedDate));
            }

            displayPlaylists(playlists);
            currentSort = sortBy;
        })
        .catch(error => console.error('Error loading playlist data:', error));
}

function displayPlaylists(playlists) {
    const container = document.getElementById('playlistContainer');
    container.innerHTML = '';

    playlists.forEach(playlist => {
        const header = document.createElement('div');
        header.className = 'playlist-header';
        header.textContent = playlist.name + ' (Last Modified: ' + playlist.lastModifiedDate + ')';
        header.addEventListener('click', function () {
            const content = this.nextElementSibling;
            content.style.display = content.style.display === 'block' ? 'none' : 'block';
        });

        const playlistContainer = document.createElement('div');
        playlistContainer.className = 'playlist-container';

        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');
        const headRow = document.createElement('tr');
        ['Track Name', 'Artist', 'Album', 'Added Date'].forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            headRow.appendChild(th);
        });

        // Add 'Add All' checkbox and text in the same cell
        const addAllTh = document.createElement('th');
        addAllTh.innerHTML = 'Add All <input type="checkbox" id="addAllCheckbox">';
        addAllTh.querySelector('input').addEventListener('change', function () {
            const checkboxes = tbody.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => checkbox.checked = this.checked);
            updateSelectedCount();
        });
        headRow.appendChild(addAllTh);

        thead.appendChild(headRow);
        table.appendChild(thead);

        playlist.items.forEach(item => {
            const tr = document.createElement('tr');
            ['trackName', 'artistName', 'albumName', 'addedDate'].forEach(key => {
                const td = document.createElement('td');
                td.textContent = item[key] || (item.track ? item.track[key] : 'N/A');
                tr.appendChild(td);
            });

            // Add individual checkboxes for download
            const addDownloadTd = document.createElement('td');
            const addDownloadCheckbox = document.createElement('input');
            addDownloadCheckbox.type = 'checkbox';
            addDownloadCheckbox.addEventListener('change', function () {
                updateSelectedCount();
            });
            addDownloadTd.appendChild(addDownloadCheckbox);
            tr.appendChild(addDownloadTd);

            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        playlistContainer.appendChild(table);
        container.appendChild(header);
        container.appendChild(playlistContainer);
    });
}

function loadByArtist() {
    fetch('Playlist1.json')
        .then(response => response.json())
        .then(data => {
            let artists = {};

            data.playlists.forEach(playlist => {
                playlist.items.forEach(item => {
                    const artistName = item.artistName || (item.track ? item.track.artistName : 'Unknown Artist');
                    if (!artists[artistName]) {
                        artists[artistName] = [];
                    }
                    artists[artistName].push(item);
                });
            });

            const sortedArtists = Object.keys(artists).sort();

            displayArtists(sortedArtists, artists);
            currentSort = 'artist'; 
        })
        .catch(error => console.error('Error loading artist data:', error));
}

function displayArtists(sortedArtists, artists) {
    const container = document.getElementById('playlistContainer');
    container.innerHTML = ''; 

    sortedArtists.forEach(artist => {
        const header = document.createElement('div');
        header.className = 'playlist-header';
        header.textContent = artist;
        header.addEventListener('click', function () {
            const content = this.nextElementSibling;
            content.style.display = content.style.display === 'block' ? 'none' : 'block';
        });

        const artistContainer = document.createElement('div');
        artistContainer.className = 'playlist-container';

        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');
        const headRow = document.createElement('tr');
        ['Track Name', 'Album', 'Added Date'].forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            headRow.appendChild(th);
        });

        // Add 'Add All' checkbox directly in the same cell
        const addAllTh = document.createElement('th');
        addAllTh.innerHTML = 'Add All <input type="checkbox" id="addAllCheckboxArtist">';
        addAllTh.querySelector('input').addEventListener('change', function () {
            const checkboxes = tbody.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => checkbox.checked = this.checked);
            updateSelectedCount();
        });
        headRow.appendChild(addAllTh);

        thead.appendChild(headRow);
        table.appendChild(thead);

        artists[artist].forEach(item => {
            const tr = document.createElement('tr');
            ['trackName', 'albumName', 'addedDate'].forEach(key => {
                const td = document.createElement('td');
                td.textContent = item[key] || (item.track ? item.track[key] : 'N/A');
                tr.appendChild(td);
            });

            // Add individual checkboxes for download
            const addDownloadTd = document.createElement('td');
            const addDownloadCheckbox = document.createElement('input');
            addDownloadCheckbox.type = 'checkbox';
            addDownloadCheckbox.addEventListener('change', function () {
                updateSelectedCount();
            });
            addDownloadTd.appendChild(addDownloadCheckbox);
            tr.appendChild(addDownloadTd);

            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        artistContainer.appendChild(table);
        container.appendChild(header);
        container.appendChild(artistContainer);
    });
}

function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('#playlistContainer input[type="checkbox"]:checked');
    selectedCount = checkboxes.length;
    document.getElementById('selectedCount').textContent = selectedCount;
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Function to switch between Song/Album in the Download Manager
function selectMode(mode) {
    selectedMode = mode;

    const songButton = document.getElementById('songButton');
    const albumButton = document.getElementById('albumButton');

    if (mode === 'song') {
        songButton.classList.add('selected');
        albumButton.classList.remove('selected');
    } else {
        albumButton.classList.add('selected');
        songButton.classList.remove('selected');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadPlaylists(); 
});
