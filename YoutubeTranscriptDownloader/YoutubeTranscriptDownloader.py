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
# ==================================================================

# =========================== IMPORTS =============================
import os, re, csv, json, hashlib, logging, isodate
from tqdm import tqdm
from prettyPrint import *
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
        "youtube_video_id": r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?].*)?",
    },
}


def load_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                user_config = json.load(f)
                config.update({k: v for k, v in user_config.items() if v is not None})
        except Exception as e:
            eprint(f"Error loading '{CONFIG_FILE}': {e}. Using default settings.")

    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, "r") as f:
                api_key_data = json.load(f)
                config["API_KEY"] = api_key_data.get("youtube").get("api_key")
        except Exception as e:
            eprint(f"Error loading '{API_KEY_FILE}': {e}. API key not loaded.")
    else:
        eprint(f"API key file '{API_KEY_FILE}' not found.")

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
    pattern = REGEX_PATTERNS.get("sanitize_filename", r"[^\w\-\s]")
    sanitized_filename = re.sub(pattern, "", name).strip()[:max_length]
    return sanitized_filename if sanitized_filename else "untitled"


def sanitize_text(text):
    if not text:
        return ""
    regex_special_chars = r"[\\^$.|?*+(){}[\]]"
    emoji_and_non_utf8 = r"[^\u0000-\u007F\u0080-\uFFFF]"
    multiple_spaces = r"\s+"
    text = re.sub(regex_special_chars, "", text)
    text = re.sub(emoji_and_non_utf8, "", text)
    text = re.sub(multiple_spaces, " ", text)
    return text.strip()


def parse_time_format(seconds):
    if not isinstance(seconds, (int, float)):
        raise ValueError(f"Expected a number, got: {seconds}")
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return (
        f"{hours:02}:{minutes:02}:{seconds:02}"
        if hours
        else f"{minutes:02}:{seconds:02}"
    )


def fetch_video_metadata(video_id):
    """Fetch video metadata using YouTube Data API."""
    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)
        response = (
            youtube.videos().list(part="snippet,contentDetails", id=video_id).execute()
        )
        if "items" in response and response["items"]:
            item = response["items"][0]
            snippet = item["snippet"]
            content_details = item["contentDetails"]

            title = snippet["title"]
            channel_title = snippet["channelTitle"]
            publish_date = snippet["publishedAt"][:10]
            duration = content_details["duration"]
            tags = snippet.get("tags", [])

            return {
                "title": title,
                "channel_title": channel_title,
                "publish_date": publish_date,
                "duration": duration,
                "tags": tags,
            }
        logging.warning(f"No metadata found for video ID: {video_id}")
    except Exception as e:
        logging.error(f"Error fetching metadata for video ID {video_id}: {e}")
    return {}


def fetch_single_video(video_url=None, metadata=None):
    """
    Fetch transcript for a single video using metadata if provided,
    otherwise fetch metadata using the YouTube Data API.
    """
    if video_url is None:
        video_url = input("Enter the video URL: ")

    pattern = REGEX_PATTERNS.get(
        "youtube_video_id", r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?].*)?"
    )
    match = re.search(pattern, video_url)
    if not match:
        wprint("Invalid URL. Must contain a valid YouTube video ID.")
        return

    video_id = match.group(1)

    # Validate provided metadata
    if metadata:
        required_keys = {"title", "channel_title", "publish_date", "duration", "tags"}

        # Check that all keys are present and their values are non-empty/valid
        is_metadata_valid = all(
            key in metadata and metadata[key] not in [None, "", []]
            for key in required_keys
        )

        if is_metadata_valid:
            print(f"Using provided metadata for video ID {video_id}")
        else:
            wprint(
                f"Incomplete or invalid metadata for video ID {video_id}. Fetching from API."
            )
            metadata = fetch_video_metadata(video_id)
    else:
        metadata = fetch_video_metadata(video_id)

    # If no metadata could be fetched, skip this video
    if not metadata:
        wprint(f"Failed to fetch metadata for video ID {video_id}. Skipping.")
        return

    # Fetch transcript
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # Save transcript and metadata
        save_transcript(
            video_url,
            transcript,
            metadata.get("channel_title", "Unknown"),
            metadata.get("title", "Unknown"),
            metadata.get("publish_date", "Unknown"),
        )
        iprint(f"Transcript for {metadata.get('title', 'Unknown')} saved successfully.")
    except TranscriptsDisabled:
        wprint("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        wprint("No transcript found for this video.")
    except Exception as e:
        eprint(f"An error occurred: {e}")


def get_channel_id_from_url(url):
    """Extract the channel ID from a YouTube URL or handle."""
    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)
        if "/@" in url:  # Handle or username
            handle = url.split("/@")[-1]
            response = (
                youtube.search()
                .list(part="snippet", type="channel", q=handle, maxResults=1)
                .execute()
            )
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
        eprint(f"An error occurred: {e}")
        return None


def parse_iso8601_duration(iso_duration):
    """Convert ISO 8601 duration (e.g., 'PT1H2M30S') to seconds."""
    try:
        duration = isodate.parse_duration(iso_duration)
        return int(duration.total_seconds())
    except Exception as e:
        logging.error(f"Error parsing duration '{iso_duration}': {e}")
        return 0  # Default to 0 seconds if parsing fails


def fetch_channel_videos(channel_url):
    """Fetch all public videos from a channel's uploads playlist with detailed metadata."""
    channel_id = get_channel_id_from_url(channel_url)
    if not channel_id:
        eprint("Failed to retrieve channel ID.")
        return

    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)

        # Get the uploads playlist ID
        channel_response = (
            youtube.channels()
            .list(part="contentDetails,snippet", id=channel_id)
            .execute()
        )
        uploads_playlist_id = channel_response["items"][0]["contentDetails"][
            "relatedPlaylists"
        ]["uploads"]
        channel_name = sanitize_filename(
            channel_response["items"][0]["snippet"]["title"]
        )

        videos = []
        next_page_token = None

        while True:
            # Fetch video IDs from playlistItems().list
            playlist_response = (
                youtube.playlistItems()
                .list(
                    playlistId=uploads_playlist_id,
                    part="snippet",
                    maxResults=50,
                    pageToken=next_page_token,
                )
                .execute()
            )

            video_ids = []
            for item in playlist_response.get("items", []):
                snippet = item.get("snippet", {})
                resource_id = snippet.get("resourceId", {})
                video_id = resource_id.get("videoId")
                if video_id:
                    video_ids.append(video_id)
                else:
                    wprint(f"Skipping invalid item: {item}")

            # Fetch detailed metadata for the video IDs
            if video_ids:
                videos_response = (
                    youtube.videos()
                    .list(
                        part="snippet,contentDetails",
                        id=",".join(video_ids),
                    )
                    .execute()
                )

                for video in videos_response.get("items", []):
                    snippet = video.get("snippet", {})
                    content_details = video.get("contentDetails", {})
                    raw_duration = content_details.get("duration", "Unknown")
                    duration_seconds = parse_iso8601_duration(raw_duration)
                    formatted_duration = parse_time_format(duration_seconds)

                    videos.append(
                        [
                            video["id"],
                            snippet.get("title", "Unknown"),
                            snippet.get("tags", []),
                            snippet.get("channelTitle", "Unknown"),
                            snippet.get("publishedAt", "Unknown"),
                            formatted_duration,
                        ]
                    )

            next_page_token = playlist_response.get("nextPageToken")
            if not next_page_token:
                break

        # Save videos to a CSV file
        channel_dir = os.path.join("transcripts", channel_name)
        os.makedirs(channel_dir, exist_ok=True)

        output_file = os.path.join(channel_dir, f"{channel_name}.csv")
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Video ID",
                    "Title",
                    "Tags",
                    "Channel Title",
                    "Publish Date",
                    "Duration",
                ]
            )
            writer.writerows(videos)

        iprint(f"Fetched {len(videos)} videos. Saved to {output_file}.")

        # Ask if the user wants to fetch transcripts for the videos, defaulting to yes on enter
        fetch_transcripts = (
            input("\nDo you want to fetch transcripts for these videos? [Y/n]: ")
            .strip()
            .lower()
        )
        if fetch_transcripts in ["", "y", "yes"]:
            process_file_with_video_urls(output_file)

    except Exception as e:
        logging.error(f"Error fetching channel videos: {e}")
        eprint(f"An error occurred: {e}")


def fetch_playlist_videos(playlist_url):
    """Fetch all videos from a YouTube playlist."""
    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)

        # Get the playlist ID from URL
        if "/playlist" in playlist_url:
            playlist_id = playlist_url.split("?list=")[-1]
        else:
            raise ValueError("Invalid playlist URL format")

        videos = []
        next_page_token = None
        channel_name = None

        while True:
            # Fetch video IDs from playlistItems().list
            playlist_response = (
                youtube.playlistItems()
                .list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token,
                )
                .execute()
            )

            video_ids = []
            for item in playlist_response.get("items", []):
                snippet = item["snippet"]
                resource_id = snippet.get("resourceId", {})
                video_id = resource_id.get("videoId")
                if video_id:
                    video_ids.append(video_id)
                else:
                    wprint(f"Skipping invalid item: {item}")

            # Fetch detailed metadata for the video IDs
            if video_ids:
                videos_response = (
                    youtube.videos()
                    .list(
                        part="snippet,contentDetails",
                        id=",".join(video_ids),
                    )
                    .execute()
                )

                for video in videos_response.get("items", []):
                    snippet = video["snippet"]
                    content_details = video["contentDetails"]
                    raw_duration = content_details.get("duration", "Unknown")
                    duration_seconds = parse_iso8601_duration(raw_duration)
                    formatted_duration = parse_time_format(duration_seconds)

                    videos.append(
                        [
                            video["id"],
                            snippet.get("title", "Unknown"),
                            snippet.get("tags", []),
                            snippet.get("channelTitle", "Unknown"),
                            snippet.get("publishedAt", "Unknown"),
                            formatted_duration,
                        ]
                    )
                    if not channel_name:
                        channel_name = snippet.get("channelTitle")

            next_page_token = playlist_response.get("nextPageToken")
            if not next_page_token:
                break

        # Save videos to a CSV file
        filename = sanitize_filename(channel_name)
        output_file = f"transcripts/{filename}/{filename}.csv"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Video ID",
                    "Title",
                    "Tags",
                    "Channel Title",
                    "Publish Date",
                    "Duration",
                ]
            )
            writer.writerows(videos)

        iprint(f"Fetched {len(videos)} videos. Saved to {output_file}.")

        # Ask if the user wants to fetch transcripts for the videos, defaulting to yes on enter
        fetch_transcripts = (
            input("\nDo you want to fetch transcripts for these videos? [Y/n]: ")
            .strip()
            .lower()
        )
        if fetch_transcripts in ["", "y", "yes"]:
            process_file_with_video_urls(output_file)

    except Exception as e:
        logging.error(f"Error fetching playlist videos: {e}")
        eprint(f"An error occurred: {e}")


def process_file_with_video_urls(file_path=None):
    """Process a file containing video URLs and fetch transcripts for each video."""
    if file_path is None:
        file_path = input("Enter the path to the file (Text/CSV): ").strip()
    if not os.path.exists(file_path):
        wprint("File not found. Please try again.")
        return

    is_csv = file_path.endswith(".csv")
    urls = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if is_csv:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    urls.append(f"https://www.youtube.com/watch?v={row[0].strip()}")
            else:
                for line in f.readlines():
                    video_id = line.strip()
                    urls.append(
                        f"https://www.youtube.com/watch?v={video_id}"
                        if not video_id.startswith("https://")
                        else video_id
                    )

        for url in tqdm(urls, desc="Processing URLs", dynamic_ncols=True):
            fetch_single_video(url)

    except Exception as e:
        eprint(f"An error occurred while processing the file: {e}")


def find_duplicate_transcripts():
    """Find duplicate transcripts in the transcripts directory."""
    transcripts_dir = input("Enter the path to search for duplicates: ")
    if not os.path.exists(transcripts_dir):
        wprint("Directory does not exist.")
        return

    hashes = {}
    duplicates = []

    for root, _, files in os.walk(transcripts_dir):
        for file in files:
            if file.endswith(".json"):
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
        iprint(f"Saved duplicate transcripts to {output_file}.")
    else:
        iprint("No duplicate transcripts found.")


def save_transcript(video_url, transcript, channel_name, video_title, publish_date):
    """Save transcript and metadata to a JSON file."""
    sanitized_title = sanitize_filename(video_title)
    channel_dir = os.path.join("transcripts", sanitize_filename(channel_name))
    os.makedirs(channel_dir, exist_ok=True)

    metadata = fetch_video_metadata(video_url.split("v=")[-1].split("&")[0])

    transcript_data = {
        "metadata": {
            "video_url": video_url,
            "channel_name": channel_name,
            "video_title": video_title,
            "publish_date": publish_date,
            "duration": metadata.get("duration", "Unknown"),
            "tags": metadata.get("tags", []),
        },
        "transcript": [
            {
                "text": sanitize_text(entry["text"]),
                "at": parse_time_format(entry["start"]),
            }
            for entry in transcript
        ],
    }

    filename = os.path.join(channel_dir, f"{sanitized_title}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=4, ensure_ascii=False)


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
    while True:
        iprint(
            """
Main Menu
1. Get video transcript
2. Get multiple transcripts from video list
3. Fetch channel videos and save to CSV
4. Fetch playlist videos and save to CSV
5. Find duplicate transcripts
6. Quit
"""
        )
        choice = input("Enter your choice: ")
        if choice == "1":
            fetch_single_video()
        elif choice == "2":
            process_file_with_video_urls()
        elif choice == "3":
            fetch_channel_videos(input("Enter channel URL: "))
        elif choice == "4":
            fetch_playlist_videos(input("Enter playlist URL: "))
        elif choice == "5":
            find_duplicate_transcripts()
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main_menu()
