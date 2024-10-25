![titleASCII](/assets/images/unSpootify.png)



![UnSpootify](https://img.shields.io/badge/Version-1.0.0-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-active-brightgreen)

## Overview

**unSpootify** is a web based GUI built on [slsk-batchdl](https://github.com/fiso64/slsk-batchdl) to help users effectively convert their Spotify library into a local MP3 archive. Basically, if you're addicted to Spotify but crave total control of your music listenning experience, this repository is your first step. 

**unSpootify** features an interactive table of most of sldl's parameters which can be selected to effortlessly formulate an sldl command. Thanks to [slsk-batchdl's](https://github.com/fiso64/slsk-batchdl) wide range of input data, this allows for user friendly downloading of Spotify playlists and a tool in development for converting Spotify user data. 

![unSpootify](/assets/images/screenshot.png)


## Usage

To get started with **unSpootify**, follow the instructions below for UNIX and OSX systems:

1. **Acquire Spotify User Data**
   First, you'll need to request your Spotify Library data. Sometimes this can take over a week so the sooner the better. More information on how to get your data can be found [here](https://www.spotify.com/us/account/privacy/).
2. **Clone the repository:**
   Once you've acquired your data, go ahead and get this repository set up. Simply copy the following lines into your terminal of choice:
   ```
   git clone git@github.com:tyndalestutz/unSpootify.git
   cd unSpootify
   ```
3. **Plug-In Playlist-data.json**
   Now you'll need to copy your Spotify data over to this repository on your local machine. From the downloaded data folder, locate Playlist1.json and move it to this directory. 
4. **Begin Conversion**
   This might take a little bit of work since some of the tools here rely on SoulSeek which requires a little bit of human intervention. 
5. **Go Buy an iPod**
   With all your music now downloaded, you can grab an iPod and live the 2000's Audiophile dream. Also check out [iFlash](https://www.iflash.xyz/) if you're a fan of iPods but need more space. 
6. **Don't Sue Me**
   Not totally sure why you would sue me but if you're thinking about it, stop. 

## Contributions

This project will be a work in progress for awhile. If you have recommendations or would like to help improve anything, you're help is more than welcome!

Just follow these steps:

1. Fork the repository to your own GitHub account.
2. `git clone` your forked repository.
3. `git checkout -b <my-branch-name>` to create a branch, replacing with your actual branch name.
4. Add your features or bug fixes.
5. `git push origin <my-branch-name>` to push your branch to your forked repository.
6. Head back to the upstream `tyndalestutz/bh_vis` repository and submit a pull request using your branch from your forked repository.
---