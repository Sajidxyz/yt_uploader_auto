from yt_dlp import YoutubeDL
import os
import json

def get_yt(url, save_path='.'):
    """
    Download YouTube video, transcript, and save metadata to JSON.
    Tracks processed videos in 'process_track.json' and skips duplicates.
    Always overwrites yt_video.mp4, yt_metadata.json, and yt_transcript.txt.
    """
    result = {
        'title': None,
        'description': None,
        'tags': None,
        'url': url,
        'video_file': None,
        'transcript_file': None
    }

    # File paths
    video_file = os.path.join(save_path, "yt_video.mp4")
    json_file = os.path.join(save_path, "yt_metadata.json")
    transcript_file = os.path.join(save_path, "yt_transcript.txt")
    track_file = os.path.join(save_path, "process_track.json")

    # ✅ Load or create tracking file
    if os.path.exists(track_file):
        with open(track_file, 'r', encoding='utf-8') as f:
            processed = json.load(f)
    else:
        processed = []

    # ✅ Check if this URL was already processed
    for item in processed:
        if item.get('url') == url:
            print("⚠️ This video is already processed. Skipping download.")
            return result  # ⛔ Stop function early

    # ✅ Delete old files if they exist
    for fpath in [video_file, json_file, transcript_file]:
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f"🧹 Old {os.path.basename(fpath)} deleted")

    try:
        # ✅ yt-dlp settings
        ydl_opts = {
            'outtmpl': os.path.join(save_path, 'yt_video.%(ext)s'),
            'format': 'best',
            'quiet': False,
            'noplaylist': True,
            'overwrites': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'skip_download': False
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)

            result['title'] = info_dict.get('title')
            result['description'] = info_dict.get('description')
            result['tags'] = info_dict.get('tags', [])
            result['video_file'] = video_file

            # ✅ Extract transcript from subtitles
            transcript_text = ""
            subtitles = info_dict.get('subtitles', {})
            automatic_captions = info_dict.get('automatic_captions', {})
            
            # Try manual subtitles first, then automatic
            all_subs = subtitles if subtitles else automatic_captions
            
            if all_subs and 'en' in all_subs:
                # Get the subtitle data
                sub_list = all_subs['en']
                for sub in sub_list:
                    if 'url' in sub:
                        # Download and parse subtitle
                        try:
                            sub_data = ydl.urlopen(sub['url']).read().decode('utf-8')
                            # Basic cleanup for common subtitle formats
                            lines = sub_data.split('\n')
                            for line in lines:
                                # Skip timestamp lines and empty lines
                                if '-->' not in line and line.strip() and not line.strip().isdigit():
                                    transcript_text += line.strip() + " "
                            break
                        except:
                            continue
            
            # ✅ Save transcript to file
            if transcript_text:
                with open(transcript_file, 'w', encoding='utf-8') as f:
                    f.write(transcript_text.strip())
                result['transcript_file'] = transcript_file
                print("✅ Transcript saved as: yt_transcript.txt")
            else:
                print("⚠️ No transcript available for this video")

            # ✅ Save metadata
            metadata = {
                'title': result['title'],
                'description': result['description'],
                'tags': result['tags'],
                'url': url,
                'has_transcript': bool(transcript_text)
            }

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)

            # ✅ Save to process_track.json
            processed.append(metadata)
            with open(track_file, 'w', encoding='utf-8') as f:
                json.dump(processed, f, indent=4, ensure_ascii=False)

            print("\n✅ Video downloaded as: yt_video.mp4")
            print("✅ Metadata saved as: yt_metadata.json")
            print("✅ Added to process_track.json")

    except Exception as e:
        print("❌ Error while downloading:", e)

    return result