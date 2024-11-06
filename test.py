
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip
import ffmpeg
from datetime import timedelta
from moviepy.config import change_settings
import moviepy.editor as mp
import ffmpeg
import os
from PIL import Image
import re
change_settings({"IMAGEMAGICK_BINARY": "C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})

# Load environment variables from .env file
load_dotenv(override=True)

try:
    endpoint = os.getenv("VISION_ENDPOINT")
    key = os.getenv("VISION_KEY")
    if not endpoint or not key:
        raise KeyError
except KeyError:
    print("Missing environment variable 'VISION_ENDPOINT' or 'VISION_KEY'")
    print("Set them in the .env file before running this sample.")
    exit()

try:
    speech_region = os.getenv("SPEECH_REGION")
    speech_key = os.getenv("SPEECH_KEY")
    if not speech_region or not speech_key:
        raise KeyError
except KeyError:
    print("Missing environment variable 'SPEECH_KEY' or 'SPEECH_REGION'")
    print("Set them in the .env file before running this sample.")
    exit()

# Handle binarization before uploading
img_url = 'https://files.catbox.moe/1a1ku0.jpg'

# NOTE, you should probably binarize the image before using ocr services,
# The textbook here has thin pages, and the OCR ocassionally picks up characters on the other page

client = ImageAnalysisClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

result = client.analyze_from_url(
    image_url= img_url,
    visual_features=[VisualFeatures.READ]
)


result_string = ''
lines = []
if result.read is not None:
    for line in result.read.blocks[0].lines:
       result_string += line.text
       lines.append(line.text)



speech_config = speechsdk.SpeechConfig(subscription=os.environ['SPEECH_KEY'], region=os.environ.get('SPEECH_REGION'))
speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural" # Can edit voices here

audio_config = speechsdk.audio.AudioOutputConfig(filename="audio.mp3")
speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3)

synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)


word_boundaries = []


line_ptr = 0
def on_word_boundary(evt):
    word_boundaries.append({
        'text': evt.text,
        'offset': evt.audio_offset / 10000000
    })


synthesizer.synthesis_word_boundary.connect(on_word_boundary)

speech_result = synthesizer.speak_text_async(result_string).get()

word_ptr = 0
start_time = 0
sentences = []
while(word_ptr != len(word_boundaries)):
    curr_chars = 0
    while(word_ptr != len(word_boundaries) and curr_chars < len(lines[line_ptr])):
        curr_chars += len(word_boundaries[word_ptr]['text'])
        word_ptr += 1
    time = word_boundaries[word_ptr - 1]['offset']
    
    sentences.append({
        'text': lines[line_ptr],
        'offset': time
    })
    
    line_ptr += 1



vtt_content = "WEBVTT\n\n"
for i, word in enumerate(sentences):

    start_time = timedelta(seconds=sentences[i-1]['offset']) if i-1 >= 0 else 0
    end_time = timedelta(seconds=sentences[i]['offset'])
    

    start_time_str = str(start_time)[:-3] if '.' in str(start_time) else f"{start_time}.000"
    if start_time == 0:
        start_time_str = '0:00:00.000'
    end_time_str = str(end_time)[:-3] if '.' in str(end_time) else f"{end_time}.000"
    
    vtt_content += f"{i + 1}\n"
    vtt_content += f"{start_time_str} --> {end_time_str}\n"
    vtt_content += f"{word['text']}\n\n"


with open("subtitles.vtt", "w", encoding="utf-8") as vtt_file:
    vtt_file.write(vtt_content)

def create_video_with_subtitles(mp3_file, vtt_file, background_image, output_file, resolution=(560, 420)):

    audio = mp.AudioFileClip(mp3_file)
    background = mp.ImageClip(background_image).set_duration(audio.duration)
    video = background.set_audio(audio)
    temp_output = "temp_output.mp4"
    video.write_videofile(temp_output, fps=24)


    (
        ffmpeg
        .input(temp_output)
        .output(
            output_file,
            vf=f"subtitles={vtt_file}:force_style='FontSize=18,Alignment=10'"  
        )
        .run(overwrite_output=True)
    )

    
    os.remove(temp_output)
    
img_file = "background.jpg"
vtt_file = "subtitles.vtt"
wav_file = "audio.mp3"
output_file = "output.mp4"
create_video_with_subtitles(wav_file, vtt_file, img_file, output_file)
