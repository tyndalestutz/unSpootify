![titleASCII](/assets/images/unSpootify.png)

![UnSpootify](https://img.shields.io/badge/Version-1.0.0-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-active-brightgreen)

---

## Overview

**UnSpootify** is a web-based interface for [slsk-batchdl](https://github.com/fiso64/slsk-batchdl), created for those who want complete control of their music collection but aren't experienced with bash. This GUI is designed to help users convert Spotify libraries into personal MP3 archives quickly and efficiently. If you're tied to Spotify but long for the freedom of your own collection of downloaded music, **UnSpootify** is your first step.

![unSpootify](/assets/images/screenshot.png)


## Installation and Usage

**System Requirements:**  
- **Operating System:** UNIX-based (Linux/macOS)
- **Dependencies:** [SoulSeek](https://www.slsknet.org/), [slsk-batchdl](https://github.com/fiso64/slsk-batchdl)

***NOTE: These tools have not been tested on Windows***
### Step 1: Acquire Spotify User Data
Request your Spotify Library data. (Note: It may take over a week, so request it early!) Follow the [Spotify data request guide](https://www.spotify.com/us/account/privacy/).

while it is more efficient to have your Spotify data locally, you can also skip ahead and simply find the link to a public playlist you'd like to download (if you plan to download albums from each song, choose a playlist that's less than 30 songs as downloading will take a while). 

To keep track of the playlists you're downloading, it is recommended to save the links to each playlist in a `.txt` file in this repository for future reference.

### Step 2: Clone Repositories and Set Up Requirements

1. **Clone `unSpootify` and `slsk-batchdl` Repositories**  
   First, clone both this repository and the `slsk-batchdl` repository, which is required for playlist downloading.
   ```
   git clone https://github.com/tyndalestutz/unSpootify  
   cd unSpootify  
   git clone https://github.com/fiso64/slsk-batchdl
   ```
2. **Install .NET SDK**  
   `slsk-batchdl` requires the .NET SDK for publishing.

   - **For Unix-based Systems (Linux)**:  
     Run the following command:  
   ``` 
     sudo apt update  
     sudo apt install -y dotnet-sdk-6.0
   ```
   - **For macOS**:  
     Make sure Homebrew is installed, then run:  
   ```
     brew install --cask dotnet-sdk  
   ```
3. **Publish `slsk-batchdl` for Your Platform**  
   Navigate to the `slsk-batchdl` directory and publish the app using the provided script:
   ```
   cd slsk-batchdl
   ```
   - **For Unix (Linux)**:  
   ```
     bash publish.sh -r linux-x64
   ```
   - **For macOS (Apple Silicon)**:  
   ```
     bash publish.sh -r osx-arm64
   ```
   - **For macOS (Intel)**:  
   ```  
     bash publish.sh -r osx-x64
   ```
4. **Update Path in `server.js` (macOS Users Only)**  
   If you are using macOS, update the `sldlDirectory` path in line 16 of `server.js` found in the `link-playlistDownloader` folder:  

   - Replace: 
   ``` 
     const sldlDirectory = path.join(__dirname, '../slsk-batchdl/slsk-batchdl/bin/Release/net6.0/linux-x64/publish');
   ```
   - With:  
   ```
     const sldlDirectory = path.join(__dirname, '../slsk-batchdl/slsk-batchdl/bin/Release/net6.0/osx-arm64/publish');
   ```
### Step 3: Add Playlist Data

In the downloaded Spotify data folder, locate the file `Playlist1.json` and copy it into the main unSpootify directory. If you are downloading directly from a Spotify playlist link, skip this step and proceed to Step 4.

### Step 4: Start the Application

1. **Launch unSpootify**  
   While in the unSpootify directory, start the server with the following command:
   ```
   cd link-playlistDownloader
   node server.js
   ```
2. **Open the Application**  
   Go to [https://localhost:3000](http://localhost:3000) in your web browser.

3. **Begin Downloading**  
   In the web interface:  
   - Enter a SoulSeek username and password of your choice.  
   - Select your download folder.  
   - Paste the link to your Spotify playlist.  

   Adjust any desired parameters in the `Basic` and `Advanced` Options panels, and start downloading your music!

### Step 5: Get an iPod
With your favorite Spotify songs now downloaded, get yourself an iPod and live the early 2000's audiophile dream! Further, if you find that your library is too large for your iPod, check out [iFlash](https://www.iflash.xyz/) to expand your iPod’s storage. 


## Troubleshooting

- **Port Error:** If sldl displays a port error, adjust the listening port in the advanced options and retry. Some networks restrict SoulSeek's default ports.
- **Path Error:** If you encounter a path error, retrieve your download folder path manually (macOS users can use `Show Path`) and paste it directly into **UnSpootify**.
- **No Results:** As SoulSeek is a peer-to-peer network, some songs may yield no results. You can try the `-d` desperate mode and disable `--fast-search` to broaden the search range.



## Development Roadmap

- **Feature Expansions:** In progress, including tools for expanded data handling.
- **Enhanced GUI:** Refinements for better user interactivity and customizability.


## Contributions

Contributions are welcome! To contribute:
1. **Fork** this repository.
2. **Clone** your fork:
    
        git clone https://github.com/your-username/unSpootify.git
        cd unSpootify

3. **Create a new branch** for your feature:
    
        git checkout -b feature/your-feature-name

4. Implement your changes and commit.
5. **Push** to your branch:
    
        git push origin feature/your-feature-name

6. Submit a **pull request** to the original repository.

<br></br>

**License:** MIT  
For detailed terms, please refer to the LICENSE file.
