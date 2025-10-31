import os
import glob
from pydub import AudioSegment

# --- Tell pydub exactly where ffmpeg is (set immediately on import) ---
AudioSegment.converter = r"E:\PycharmProjects\discord_bot\pythonProject\converter\ffmpeg.exe"
AudioSegment.ffprobe = r"E:\PycharmProjects\discord_bot\pythonProject\converter\ffprobe.exe"

def convert_file(mp3_path=None, ogg_path=None, silence_ms=0):
    # --- Configuration ---
    INPUT_FOLDER = r"E:\PycharmProjects\discord_bot\pythonProject\downloads"
    EXPORT_FOLDER = r"E:\PycharmProjects\discord_bot\pythonProject\converted"
    os.makedirs(EXPORT_FOLDER, exist_ok=True)

    # If specific paths are given, convert only that file
    if mp3_path and ogg_path:
        try:
            audio = AudioSegment.from_mp3(mp3_path)
            
            # Add silence to the beginning if requested
            if silence_ms > 0:
                silence = AudioSegment.silent(duration=silence_ms)
                audio = silence + audio
                print(f"Added {silence_ms}ms of silence to the beginning")
            
            audio.export(ogg_path, format="ogg", codec="libvorbis")
            print(f"Successfully saved {ogg_path}")
            return True
        except Exception as e:
            print(f"Failed to convert {mp3_path}: {e}")
            raise e  # Re-raise the exception so the Discord command can handle it
        
    # If no specific paths given, don't do batch conversion automatically
    # This prevents unwanted batch conversion when the module is imported
    return False

def batch_convert():
    """Separate function for batch conversion - call this explicitly if needed"""
    INPUT_FOLDER = r"E:\PycharmProjects\discord_bot\pythonProject\downloads"
    EXPORT_FOLDER = r"E:\PycharmProjects\discord_bot\pythonProject\converted"
    
    mp3_files = glob.glob(os.path.join(INPUT_FOLDER, "*.mp3"))
    if not mp3_files:
        print(f"No MP3 files found in {INPUT_FOLDER}.")
        return

    for mp3_file_path in mp3_files:
        file_name = os.path.basename(mp3_file_path)
        base_name, _ = os.path.splitext(file_name)
        ogg_file_path = os.path.join(EXPORT_FOLDER, f"{base_name}.ogg")

        if os.path.exists(ogg_file_path):
            print(f"Skipping {file_name}, already converted.")
            continue

        print(f"\n--- Converting: {file_name} ---")
        try:
            audio = AudioSegment.from_mp3(mp3_file_path)
            audio.export(ogg_file_path, format="ogg", codec="libvorbis")
            print(f"Successfully saved {ogg_file_path}")
        except Exception as e:
            print(f"Failed to convert {file_name}: {e}")



