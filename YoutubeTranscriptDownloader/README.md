# YouTube Transcript Downloader

---

## Usage
Run the script:
```bash
python YoutubeTranscriptDownloader.py
```

### Main Menu Options
1. **Get Video Transcript**:
    - Fetch and save a transcript for a single video by entering its URL.

2. **Get Transcripts from Video List File**:
    - Process a file (text or CSV) with video URLs or IDs.

3. **Fetch Channel Videos and Save to File**:
    - Fetch all videos from a YouTube channel and save metadata to a CSV file.
    - Then use the CSV file for menu option 2.
    - This is intentionally set up this way so you can still remove videos you don't want the transcripts from. ie from before a certain date, a specific video title. Or you're looking for a specific video and don't want to scroll through endless pages to find it.

4. **Find Duplicate Transcripts**:
    - Detect and list duplicate transcript files in a directory.

5. **Quit**: Exit the application.

---
---

## Overview
The YouTube Transcript Downloader is a Python application for downloading transcripts from YouTube videos and channels. It uses the YouTube Data API and YouTube Transcript API to fetch video metadata and subtitles. The application can save transcripts to files, process video lists, and identify duplicate transcripts.

## Features
- **Fetch Single Video Transcript**: Download and save transcripts for individual videos.
- **Process Video Lists**: Extract transcripts from a list of video URLs or IDs in text or CSV files.
- **Channel Video Metadata**: Fetch video metadata from a YouTube channel and save it as a CSV file.
- **Duplicate Detection**: Identify duplicate transcripts in a directory.
- **Customizable Configuration**: Modify log settings, transcript filename length, and regex patterns via `config.json`.

## Requirements
- 🚨 **YouTube API key** 🚨
- Python 3.7+
- Dependencies:
  - `google-api-python-client`
  - `youtube-transcript-api`
  - `tqdm`

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Setup
1. Clone the repository or download the files.
2. Install dependencies (see above).
3. Create an API key file `API_KEY.json`:
   ```json
   {
       "API_KEY": "your_actual_api_key"
   }
   ```
4. (Optional) Configure `config.json` to customize settings.

## Configuration
The `config.json` file allows you to customize the application. Example:
```json
{
    "LOGFILE_NAME": "script.log",
    "LOGFILE_PATH": "./logs",
    "ENABLE_LOGGING": true,
    "TRANSCRIPT_FILENAME_LENGTH": 36,
    "REGEX_PATTERNS": {
        "sanitize_filename": "[^\\w\\-\\s]",
        "iso_duration": "PT(?:(\\d+)H)?(?:(\\d+)M)?(?:(\\d+)S)?",
        "youtube_video_id": "(?:v=|\\/)([0-9A-Za-z_-]{11}).*"
    }
}
```
- `"TRANSCRIPT_FILENAME_LENGTH"`: truncates filenames to max x characters, incl spaces.
- `"REGEX_PATTERNS"`
    - `"sanitize_filename"`: Removes non-standard UTF-8 characters and removes double spaces in title.
    - `"iso_duration"`: Gets the total length from the video.
    - `"youtube_video_id"`: Validates the video ID (the part after 'watch' in youtube video urls)
        - make sure they don't have any other tags such as `?t=xxx`



## File Structure
- **Main Script**: `YoutubeTranscriptDownloader.py`
- **Configuration**: `config.json`
- **API Key**: `API_KEY.json`
- **Output Directory**: Transcripts and metadata are saved in the `transcripts` directory.

## Example Workflow
1. Fetch a transcript for a single video:
   ```
   Enter the video URL: https://www.youtube.com/watch?v=example_id
   ```
2. Process a file of video URLs:
   ```
   Enter the path to the file (Text/CSV): video_list.txt
   ```
3. Fetch channel videos:
   ```
   Enter the channel URL or handle: https://www.youtube.com/@examplechannel
   ```
4. Find duplicates:
   ```
   Enter the path to search for duplicates: ./transcripts
   ```

## Logging
Logs are saved to the specified file in `config.json` (default: `./logs/script.log`). Logging can be disabled by setting `"ENABLE_LOGGING": false`.

## Known Issues
- Transcripts disabled by the channel owner cannot be downloaded.
- Missing or invalid API key results in an error.

## License
This project is open-source and available under the GNU General Public License (GPL) License.

```plaintext
https://www.gnu.org/licenses/gpl-3.0.txt
```
