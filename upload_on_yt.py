from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import pickle
import os
import json
import time
import traceback
from datetime import datetime, timedelta, time as dtime

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def authenticate_youtube():
    """Authenticate and return YouTube API client."""
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('secrect_code.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)


def get_next_upload_slot(already_scheduled_count=0):
    """
    Get the next available upload time slot in the future.
    Alternates between 9:45 AM and 7:30 PM across days.
    """
    now = datetime.now()
    print(f"\n⏰ Current time: {now.strftime('%Y-%m-%d %I:%M %p')}")

    current_day = now.date()
    slot_index = already_scheduled_count % 2  # 0: morning, 1: evening
    day_offset = already_scheduled_count // 2
    target_day = current_day + timedelta(days=day_offset)

    scheduled_time = datetime.combine(target_day, dtime(9, 45)) if slot_index == 0 else datetime.combine(target_day, dtime(19, 30))

    # Ensure scheduled time is in the future
    while scheduled_time <= now:
        slot_index = (slot_index + 1) % 2
        if slot_index == 0:
            target_day += timedelta(days=1)
            scheduled_time = datetime.combine(target_day, dtime(9, 45))
        else:
            scheduled_time = datetime.combine(target_day, dtime(19, 30))

    print(f"📅 Next upload slot: {scheduled_time.strftime('%Y-%m-%d %I:%M %p')}")
    return scheduled_time


def load_metadata(info_file):
    """Load video metadata from JSON file."""
    try:
        with open(info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Metadata file '{info_file}' not found.")
    except json.JSONDecodeError:
        print(f"⚠️ Error parsing JSON from '{info_file}'.")
    return None


def prepare_video_details(metadata, use_defaults=False):
    """Prepare video details from metadata or defaults."""
    if metadata and not use_defaults:
        title = metadata.get('title', 'Untitled Video')
        if '#shorts' not in title.lower():
            title = f"{title} #shorts"
        description = metadata.get('description', '')
        tags = metadata.get('tags', [])
    else:
        print("\nℹ️ Using default metadata...")
        title = "#shorts"
        description = "Check out this awesome short video! 🔥\n\n#shorts #viral #trending"
        tags = ['shorts', 'viral', 'trending', 'youtube', 'short']

    return {
        'title': title,
        'description': description,
        'tags': tags if isinstance(tags, list) else []
    }


def upload_video(video_file="output_video.mp4", info_file="yt_metadata.json",
                 scheduled_count=0, use_defaults=False):
    """Upload a video to YouTube with progress tracking and scheduling."""
    try:
        if not os.path.exists(video_file):
            return {"error": f"Video file '{video_file}' not found."}

        metadata = load_metadata(info_file)
        if not metadata and not use_defaults:
            response = input("\n⚠️ Metadata file not found. Use default values? (y/n): ").lower()
            use_defaults = response == 'y'
            if not use_defaults:
                return {"error": "Upload cancelled. Please provide metadata file."}

        video_details = prepare_video_details(metadata, use_defaults)
        scheduled_time = get_next_upload_slot(scheduled_count)
        scheduled_time_iso = scheduled_time.isoformat() + 'Z'  # UTC time

        print(f"\n{'=' * 60}")
        print("🎬 VIDEO UPLOAD DETAILS")
        print(f"{'=' * 60}")
        print(f"📌 Title: {video_details['title']}")
        print(f"📝 Description: {video_details['description'][:100]}...")
        print(f"🏷️ Tags: {', '.join(video_details['tags'][:5])}")
        print(f"🕒 Scheduled for: {scheduled_time.strftime('%Y-%m-%d at %I:%M %p')}")
        print(f"{'=' * 60}\n")

        print("🔑 Authenticating with YouTube...")
        youtube = authenticate_youtube()

        body = {
            'snippet': {
                'title': video_details['title'],
                'description': video_details['description'],
                'tags': video_details['tags'],
                'categoryId': '22'  # People & Blogs
            },
            'status': {
                'privacyStatus': 'private',
                'publishAt': scheduled_time_iso,
                'selfDeclaredMadeForKids': False
            }
        }

        print("🚀 Uploading video (this may take a while)...")

        # Use smaller chunks to show progress
        media = MediaFileUpload(video_file, chunksize=5 * 1024 * 1024, resumable=True, mimetype='video/mp4')
        request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

        response = None
        last_progress = -1

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress != last_progress:
                        print(f"📤 Upload progress: {progress}%")
                        last_progress = progress
                else:
                    print("⏳ Still uploading... waiting for chunk...")
                    time.sleep(3)
            except Exception as e:
                print(f"⚠️ Temporary error: {e}. Retrying in 5s...")
                time.sleep(5)
                continue

        video_id = response.get('id')
        print(f"\n✅ Upload complete!")
        print(f"🎞️ Video ID: {video_id}")
        print(f"📅 Scheduled publish: {scheduled_time.strftime('%Y-%m-%d at %I:%M %p')}")
        print(f"🔗 URL: https://www.youtube.com/watch?v={video_id}")

        return {
            'success': True,
            'video_id': video_id,
            'scheduled_time': scheduled_time.strftime('%Y-%m-%d at %I:%M %p'),
            'title': video_details['title']
        }

    except Exception as e:
        print("\n❌ An error occurred during upload:")
        traceback.print_exc()
        return {'error': f"Upload failed: {str(e)}"}


def batch_upload_videos(video_files, info_files=None, use_defaults=False):
    """Upload multiple videos with automatic scheduling."""
    results = []

    for i, video_file in enumerate(video_files):
        info_file = info_files[i] if info_files and i < len(info_files) else "yt_metadata.json"

        print(f"\n{'#' * 70}")
        print(f"🎥 Uploading video {i + 1}/{len(video_files)}: {video_file}")
        print(f"{'#' * 70}\n")

        result = upload_video(video_file, info_file, scheduled_count=i, use_defaults=use_defaults)
        results.append(result)

        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Uploaded: {result['title']}")

    print(f"\n{'=' * 60}")
    print("📊 UPLOAD SUMMARY")
    print(f"{'=' * 60}")
    successful = [r for r in results if 'success' in r]
    failed = [r for r in results if 'error' in r]

    print(f"Total videos: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        print(f"\n🗓️ Scheduled uploads:")
        for r in successful:
            print(f"  - {r['title']}")
            print(f"    Time: {r['scheduled_time']}")
            print(f"    URL: https://www.youtube.com/watch?v={r['video_id']}\n")

    return results


if __name__ == '__main__':
    print("\n☁️ Step 4: Uploading video to YouTube...")
    result = upload_video(
        video_file='output_video.mp4',
        info_file="yt_metadata.json",  # make sure this exists or is generated
        use_defaults=False
    )
    print("✅ Upload completed!")
    print("📺 YouTube Upload Response:", result)
