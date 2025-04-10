# Faba+ Tools

This repository contains tools to personalize and expand your Faba+ (and MyFaba) experience.

## Upload Custom .wav Audio Using Faba Me Cloud

Using the Faba Me sharing functionality, you can upload a .wav file directly to the MyFaba cloud and associate it with your Faba Me robots (white, blue, or red).

To upload audio, you’ll need an “Invite to Record” URL link. To generate one from the MyFaba mobile app:
1. Select: _Faba Me_ > _FABA Me White_ (or Red/Blue)  
2. Tap _+ Add New Track_ and select _Invite to Record_  
3. Copy the last 10 characters of the URL generated (e.g., `8K3TzYl2WB` for `https://studio.myfaba.com/record/8K3TzYl2WB`) as `share_id`

Use the following Python command to upload the file:

```bash
python3 myfaba_upload.py [-h] <share_id> <author> <title> <wav_file>
```
e.g.:
```bash
python3 myfaba_upload.py 8K3TzYl2WB "Author Name" "Audio Title" ./audio/test.wav
```
> [!NOTE]
> The upload may take a few minutes, depending on your internet speed and file size. Once completed, you should receive a notification on the MyFaba mobile app.


### Converting .mp3 Files to .wav
To convert .mp3 files to .wav format, you can use these commands:
- Using VLC:
```bash
vlc.exe --sout "#transcode{acodec=s16l,channels=2,samplerate=44100}:std{access=file,mux=wav,dst=audio\test.wav}" audio\test.mp3
```
- Using FFmpeg:
```bash
ffmpeg -i ./audio/test.mp3 -acodec pcm_s16le -ac 2 -ar 44100 ./audio/test.wav
```

## Manually Adding Audio Files to Faba+
You can manually add .mp3 files to an existing playlist (character) or create a new one using a customized character (new NFC tag). This requires:

1. Physical access to the microSD card by opening the Faba+ and adding content manually
2. _Optional:_ A custom NFC tag for a new character with a unique ID

### Create a New Playlist with a Custom Character
1. Place all your .mp3 files in a folder, numbering the filenames in order
2. Select a character ID to associate with the new playlist (e.g., `3101`)
3. Run the `mp32faba.sh` script as follows:

```bash
./mp32faba.sh ./mp3 3101
```
4. Copy the newly created folder (e.g., `K3101`) to the PLAYER folder on the microSD card, then insert the card back into the Faba+
5. Generate a new NFC tag using the selected character ID (e.g., `3101`) to play the newly added playlist

### Add Songs to an Existing Playlist
1. Create a local backup of the microSD content.
2. Identify or read the character ID of an existing NFC tag (e.g., `0190` for the FABA Me White robot).
3. Browse to the corresponding folder on the microSD card (e.g., `PLAYER\K0190`) and check the last file name (e.g., `02.faba`). The next file should be numbered 03.faba.
4. Place the new .mp3 files you want to add in a folder and number the filenames accordingly. Run the `mp32faba.sh` script:
```bash
./mp32faba.sh ./mp3 0190 3
```
5. Add the contents of the newly created folder (e.g., `K0190/03.faba`) to the original folder on the microSD and replace the info file with the new one. Reinsert the microSD card into the Faba+ and test the playlist with the existing character.

> [!NOTE]
> Custom audio content will not appear in the MyFaba mobile app. It is recommended to keep track of which audio files are in which folders and their respective order.

> [!IMPORTANT]
> Character IDs starting with `0xxx`, `1xxx`, or `9xxx` are reserved for original content and testing purposes. Avoid using them for custom characters.

> [!IMPORTANT]
> When creating a custom character, ensure the UID of the NFC tag is not already associated with another character ID. Do not use two tags with the same UID and different character IDs, or vice versa.

> [!WARNING]
> Always add custom content to the microSD card first, then test the tag. Using a custom tag before adding the correspondent folder may cause the Faba+ to freeze.


### Additional Information
The  `mp32faba.sh` script uses eyeD3 to edit mp3 ID3 tags. To install it, run:
```bash
pip install eyeD3
```


## Custom NFC Tags
Custom characters can be created using compatible NFC tags. The following tags have been tested and are supported: NTAG203, NTAG213, NTAG215, and NTAG216.

### Read and Write NFC Tags
TBD



## Hardware Hacks

### Remote Access to Faba+ microSD
Managing custom audio content on the Faba+ requires access to the microSD card, but disassembling the device each time is not ideal. The firmware does not include a setting to enable USB mass storage, and while the Faba Me cloud functionality works, it is limited - especially when using custom NFC tags.
One option would be to relocate the microSD card slot by creating a hole in the case and using an extension cable. However, this is not recommended, as the microSD card could be easily removed, lost, or even swallowed.

So, I came up with my own over-engineered solution: a custom PCB that controls access to the microSD card and makes its contents manageable remotely via Wi-Fi. The custom PCB fits on top of the Faba+ board, requires no additional power supply, and can be manually switched on only when needed by placing a magnet on the case - eliminating the need for an external switch.

I currently have a working prototype and finalizing the design and code.

<p align="center">
  <img src="https://github.com/60ne/faba-tools/blob/main/images/pcb_prototype.jpg?raw=true" width="490"/><br/>
  <i>Faba remote access board - Prototype v2</i>
</p>

> [!NOTE]
> The custom PCB checks whether the microSD card is currently in use by the Faba+ box before disconnecting it and making it available via WebDAV. The WebDAV interface is only activated when the Faba+ box is turned off (sleep mode).\
> It is recommended to stop the WebDAV server before turning the Faba+ box back on.

Terminal output:

```
[*] Taking control of microSD...
  [!] microSD is already in use
  [!] Please turn off Faba first

[*] Taking control of microSD...
  [+] microSD access granted
  [+] WebDAV server started: \\faba@6126\PLAYER

[*] Release microSD control...
  [+] WebDAV server stopped
  [+] microSD released
```


Remote access to files via File Explorer:

<p align="center">
  <img src="https://github.com/60ne/faba-tools/blob/main/images/remote_access.png?raw=true" width="466"/><br/>
</p>


