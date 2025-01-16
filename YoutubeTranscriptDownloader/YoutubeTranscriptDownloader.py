# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#==================================================================

# =========================== IMPORTS =============================
import os, re, csv, json, hashlib, logging
from tqdm import tqdm
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build

# =========================== CONFIGURATION =======================
CONFIG_FILE = "config.json"
API_KEY_FILE = "API_KEY.json"
DEFAULT_CONFIG = {
    "LOGFILE_NAME": "script.log",
    "LOGFILE_PATH": ".",
    "ENABLE_LOGGING": True,
    "TRANSCRIPT_FILENAME_LENGTH": 36,
    "REGEX_PATTERNS": {
        "sanitize_filename": r"[^\w\-\s]",
        "iso_duration": r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        "youtube_video_id": r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    }
}

def load_config():
    """Load configuration and API key from files with fallback to defaults."""
    config = DEFAULT_CONFIG.copy()

    # Load main config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                user_config = json.load(f)
                config.update({k: v for k, v in user_config.items() if v is not None})
        except Exception as e:
            print(f"Error loading '{CONFIG_FILE}': {e}. Using default settings.")

    # Load API key
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, "r") as f:
                api_key_data = json.load(f)
                config["API_KEY"] = api_key_data.get("API_KEY")
        except Exception as e:
            print(f"Error loading '{API_KEY_FILE}': {e}. API key not loaded.")
    else:
        print(f"API key file '{API_KEY_FILE}' not found. Ensure the API key file exists.")

    return config

CONFIG = load_config()

LOGFILE_NAME = CONFIG["LOGFILE_NAME"]
LOGFILE_PATH = CONFIG["LOGFILE_PATH"]
LOGFILE = os.path.join(LOGFILE_PATH, LOGFILE_NAME)
ENABLE_LOGGING = CONFIG["ENABLE_LOGGING"]
TRANSCRIPT_FILENAME_LENGTH = CONFIG["TRANSCRIPT_FILENAME_LENGTH"]
REGEX_PATTERNS = CONFIG["REGEX_PATTERNS"]
API_KEY = CONFIG.get("API_KEY")

if not API_KEY:
    raise ValueError("API key is missing. Please provide it in 'API_KEY.json'.")


# =========================== SETUP LOGGING ===========================
log_dir = os.path.dirname(LOGFILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    
if ENABLE_LOGGING:
    logging.basicConfig(
        filename=LOGFILE,
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.disable(logging.CRITICAL)

# ====================== HELPER FUNCTIONS ============================
def sanitize_filename(name, max_length=TRANSCRIPT_FILENAME_LENGTH):
    """Sanitize filenames for compatibility with NTFS and truncate."""
    pattern = REGEX_PATTERNS.get("sanitize_filename", r"[^\w\-\s]")
    sanitized = re.sub(pattern, "", name).strip()[:max_length]
    return sanitized if sanitized else "untitled"

def fetch_video_metadata(video_id):
    """Fetch video metadata using YouTube Data API."""
    try:
        youtube = build("youtube", "v3", developerKey=CONFIG.get("API_KEY"))
        response = youtube.videos().list(part="snippet,contentDetails,statistics", id=video_id).execute()
        if "items" in response and response["items"]:
            item = response["items"][0]
            snippet = item["snippet"]
            content_details = item["contentDetails"]
            statistics = item["statistics"]

            video_title = snippet["title"]
            channel_name = snippet["channelTitle"]
            publish_date = snippet["publishedAt"][:10]
            views = statistics.get("viewCount", "0")
            duration = format_duration(content_details["duration"])

            return video_title, channel_name, publish_date, views, duration
        else:
            logging.warning(f"No metadata found for video ID: {video_id}")
            return "Unknown Title", "Unknown Channel", "", "0", "00:00"
    except Exception as e:
        logging.error(f"Error fetching metadata for video ID {video_id}: {e}")
        return "Unknown Title", "Unknown Channel", "", "0", "00:00"


def format_duration(iso_duration):
    """Convert ISO 8601 duration to hh:mm format."""
    pattern = REGEX_PATTERNS.get("iso_duration", r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    match = re.match(pattern, iso_duration)
    if not match:
        return "00:00"

    hours, minutes, _ = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    return f"{hours:02}:{minutes:02}"

def fetch_single_video(video_url=None):
    """Fetch transcript for a single video."""
    if video_url is None:
        video_url = input("Enter the video URL: ")

    pattern = REGEX_PATTERNS.get("youtube_video_id", r"(?:v=|\/)([0-9A-Za-z_-]{11}).*")
    match = re.search(pattern, video_url)
    if not match:
        print("Invalid URL. Must contain a valid YouTube video ID.")
        return

    video_id = match.group(1)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        video_title, channel_name, *_ = fetch_video_metadata(video_id)
        save_transcript(video_url, transcript, channel_name, video_title)
        print(f"Transcript for {video_title} saved successfully.")
    except TranscriptsDisabled:
        print("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        print("No transcript found for this video.")
    except Exception as e:
        print(f"An error occurred: {e}")

def get_channel_id_from_url(url):
    """Extract the channel ID from a YouTube URL or handle."""
    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)
        if "/@" in url:  # Handle or username
            handle = url.split("/@")[-1]
            response = youtube.search().list(
                part="snippet",
                type="channel",
                q=handle,
                maxResults=1
            ).execute()
        elif "channel/" in url:  # Direct channel URL
            return url.split("channel/")[-1]
        else:
            raise ValueError("Invalid YouTube channel URL or handle.")
        
        if "items" in response and response["items"]:
            return response["items"][0]["snippet"]["channelId"]
        else:
            raise ValueError("Channel not found.")
    except Exception as e:
        logging.error(f"Error fetching channel ID for URL {url}: {e}")
        print(f"An error occurred: {e}")
        return None

def fetch_channel_videos(channel_url):
    """Fetch a list of all videos in a channel and save metadata to a CSV file."""
    channel_id = get_channel_id_from_url(channel_url)
    if not channel_id:
        print("Failed to retrieve channel ID.")
        return

    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)
        videos = []
        next_page_token = None

        # Get channel name for the file and folder
        response = youtube.channels().list(part="snippet", id=channel_id).execute()
        channel_name = sanitize_filename(response["items"][0]["snippet"]["title"])

        # Create output directory
        channel_dir = os.path.join("transcripts", channel_name)
        os.makedirs(channel_dir, exist_ok=True)

        output_file = os.path.join(channel_dir, f"{channel_name}.csv")

        while True:
            response = youtube.search().list(
                channelId=channel_id,
                part="id,snippet",
                maxResults=50,
                pageToken=next_page_token,
                type="video"
            ).execute()

            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                video_title, _, publish_date, views, duration = fetch_video_metadata(video_id)
                videos.append([video_id, video_title, publish_date, views, duration])

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Video ID", "Title", "Publish Date", "Views", "Duration (hh:mm)"])
            writer.writerows(videos)

        print(f"Fetched {len(videos)} videos. Saved to {output_file}.")

    except Exception as e:
        logging.error(f"Error fetching channel videos: {e}")
        print(f"An error occurred: {e}")

def process_file_with_video_urls():
    """Process a file containing video IDs or URLs."""
    file_path = input("Enter the path to the file (Text/CSV): ").strip()

    # Handle quoted paths and normalize them
    if file_path.startswith('"') and file_path.endswith('"'):
        file_path = file_path[1:-1]

    if not os.path.exists(file_path):
        print("File not found. Please try again.")
        return

    is_csv = file_path.endswith(".csv")
    urls = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if is_csv:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    video_id = row[0].strip()
                    urls.append(f"https://www.youtube.com/watch?v={video_id}")
            else:
                for line in f.readlines():
                    video_id = line.strip()
                    if not video_id.startswith("https://"):
                        urls.append(f"https://www.youtube.com/watch?v={video_id}")
                    else:
                        urls.append(video_id)

        for url in tqdm(urls, desc="Processing URLs", dynamic_ncols=True):
            fetch_single_video(url)

    except Exception as e:
        print(f"An error occurred while processing the file: {e}")


def find_duplicate_transcripts():
    """Find duplicate transcripts in the transcripts directory."""
    transcripts_dir = input("Enter the path to search for duplicates: ")
    if not os.path.exists(transcripts_dir):
        print("Directory does not exist.")
        return

    hashes = {}
    duplicates = []

    for root, _, files in os.walk(transcripts_dir):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                file_hash = compute_sha1(file_path)
                if file_hash in hashes:
                    duplicates.append((file_path, hashes[file_hash]))
                else:
                    hashes[file_hash] = file_path

    if duplicates:
        output_file = "duplicates.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for dup, original in duplicates:
                f.write(f"Duplicate: {dup}\nOriginal: {original}\n\n")
        print(f"Saved duplicate transcripts to {output_file}.")
    else:
        print("No duplicate transcripts found.")

def save_transcript(video_url, transcript, channel_name, video_title):
    """Save transcript to file."""
    sanitized_title = sanitize_filename(video_title)
    channel_dir = os.path.join("transcripts", sanitize_filename(channel_name))
    os.makedirs(channel_dir, exist_ok=True)

    filename = os.path.join(channel_dir, f"{sanitized_title}.txt")
    with open(filename, "w", encoding="utf-8", errors="ignore") as f:
        f.write(f"{video_url}\n{channel_name}\n{video_title}\n\n\n")
        for line in transcript:
            f.write(f"{line}\n")

def compute_sha1(file_path):
    """Compute the SHA1 hash of a file."""
    sha1 = hashlib.sha1()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha1.update(chunk)
        return sha1.hexdigest()
    except Exception as e:
        logging.error(f"Error computing SHA1 for {file_path}: {e}")
        return None

def main_menu():
    """Main navigation menu."""
    while True:
        print("\nMain Menu")
        print("1. Get video transcript")
        print("2. Get transcript from video list file")
        print("3. Fetch channel videos and save to file")
        print("4. Find duplicate transcripts")
        print("5. Quit")

        choice = input("Enter your choice: ")
        if choice == "1":
            fetch_single_video()
        elif choice == "2":
            process_file_with_video_urls()
        elif choice == "3":
            channel_url = input("Enter the channel URL or handle: ")
            fetch_channel_videos(channel_url)
        elif choice == "4":
            find_duplicate_transcripts()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


# ====================== MAIN SCRIPT ================================
if __name__ == "__main__":
    main_menu()
