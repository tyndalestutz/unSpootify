// server/spotifyToCsv.js
import fs from 'fs';
import path from 'path';
import { getTracks } from 'spotify-url-info';
import fetch from 'node-fetch';

// Convert Spotify playlist link to a CSV of track names
export async function spotifyToCsv(playlistUrl, outputFolder) {
    if (!playlistUrl.startsWith('https://open.spotify.com/playlist/')) {
        throw new Error('Invalid Spotify playlist URL');
    }

    // Get track data
    const tracks = await getTracks(playlistUrl, fetch);

    if (!tracks || tracks.length === 0) {
        throw new Error('No tracks found in Spotify playlist');
    }

    // CSV content: one track per line
    const csvContent = tracks.map(t => t.name).join('\n');

    // Ensure output folder exists
    if (!fs.existsSync(outputFolder)) fs.mkdirSync(outputFolder, { recursive: true });

    const filePath = path.join(outputFolder, 'playlist.csv');
    fs.writeFileSync(filePath, csvContent);

    return filePath;
}