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

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def authenticate_youtube():
    """Authenticate once and reuse token automatically (no manual re-verify)."""
    creds = None
    token_file = 'token.pickle'

    # Load existing credentials if available
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # If no credentials or expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing YouTube token silently...")
            creds.refresh(Request())
        else:
            print("🌐 First-time authentication — only once.")
            flow = InstalledAppFlow.from_client_secrets_file('secrect_code.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save for next runs
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)


def get_next_upload_time():
    """Return next 7:35 AM — today if not passed, else tomorrow."""
    now = datetime.now()
    scheduled_time = datetime.combine(now.date(), dtime(7, 35))
    if now >= scheduled_time:
        scheduled_time += timedelta(days=1)
    print(f"📅 Next upload: {scheduled_time.strftime('%Y-%m-%d %I:%M %p')}")
    return scheduled_time


def load_metadata(file):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def prepare_video_details(metadata=None):
    if not metadata:
        print("ℹ️ Using default video details.")
        return {
            'title': '#shorts',
            'description': 'Check out this awesome short video! 🔥\n\n#shorts #viral #trending',
            'tags': ['shorts', 'viral', 'trending']
        }
    title = metadata.get('title', 'Untitled Video')
    if '#shorts' not in title.lower():
        title += ' #shorts'
    return {
        'title': title,
        'description': metadata.get('description', ''),
        'tags': metadata.get('tags', [])
    }


def upload_video(video_file='output_video.mp4', info_file='yt_metadata.json'):
    """Upload one video, scheduled for next 7:35 AM."""
    try:
        if not os.path.exists(video_file):
            return {'error': f'File not found: {video_file}'}

        metadata = load_metadata(info_file)
        details = prepare_video_details(metadata)
        schedule_time = get_next_upload_time().isoformat() + 'Z'

        youtube = authenticate_youtube()

        body = {
            'snippet': {
                'title': details['title'],
                'description': details['description'],
                'tags': details['tags'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'private',
                'publishAt': schedule_time,
                'selfDeclaredMadeForKids': False
            }
        }

        print(f"🚀 Uploading: {details['title']}")
        media = MediaFileUpload(video_file, chunksize=5 * 1024 * 1024, resumable=True)
        request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"📤 Progress: {int(status.progress() * 100)}%")
            else:
                time.sleep(2)

        vid = response.get('id')
        print(f"\n✅ Upload done!")
        print(f"🔗 https://www.youtube.com/watch?v={vid}")
        return {'success': True, 'video_id': vid}

    except Exception as e:
        print("❌ Upload error:", e)
        traceback.print_exc()
        return {'error': str(e)}


if __name__ == '__main__':
    print("☁️ Uploading video to YouTube automatically...")
    result = upload_video()
    print("📺 Result:", result)
