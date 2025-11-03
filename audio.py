import re
import asyncio
import edge_tts
from openai import OpenAI

# ---------------------------
# Helper functions
# ---------------------------

def clean_transcript(text):
    """Remove timestamps like [00:00:27] and extra spaces."""
    cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
    return ' '.join(cleaned.split())

async def generate_voice(text, output_file="ai_dub.mp3", voice="hi-IN-SwaraNeural"):
    """
    Generate realistic AI voice using edge_tts.
    Voices examples:
        hi-IN-SwaraNeural  → Hindi Female
        hi-IN-MadhurNeural → Hindi Male
        en-US-AriaNeural   → English Female
        en-US-GuyNeural    → English Male
    """
    try:
        communicate = edge_tts.Communicate(text, voice=voice)
        await communicate.save(output_file)
        print(f"✅ Voice generated successfully: {output_file}")
    except Exception as e:
        print("❌ Voice generation error:", e)


def audio_dub(transcript_text):
    print("🧹 Cleaning transcript...")
    hindi_text = clean_transcript(transcript_text)
    print(f"\n📝 Cleaned English text:\n{hindi_text}\n")
    print("="*60)
    print("\n✅ Hindi Dubbing:\n")
    print(hindi_text)
    print("\n" + "="*60 + "\n")

    print("🎙 Generating Hindi voice audio...")
    asyncio.run(generate_voice(hindi_text, "ai_dub.mp3", voice="hi-IN-SwaraNeural"))
    
    return "ai_dub.mp3"

# ---------------------------
# Run
# ---------------------------

