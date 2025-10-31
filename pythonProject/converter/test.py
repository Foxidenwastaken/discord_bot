from pydub import AudioSegment

AudioSegment.converter = r"E:\PycharmProjects\discord_bot\pythonProject\converter\ffmpeg.exe"
AudioSegment.ffprobe = r"E:\PycharmProjects\discord_bot\pythonProject\converter\ffmpeg.exe"

if __name__ == "__main__":
    audio = AudioSegment.from_mp3(r"E:\PycharmProjects\discord_bot\pythonProject\downloads\SpotiDownloader.com_-_3on_-_Catasham.mp3")
    audio.export(r"E:\PycharmProjects\discord_bot\pythonProject\downloads\converted\test.ogg", format="ogg", codec="libvorbis")