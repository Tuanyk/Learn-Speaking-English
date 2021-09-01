"""
In this version, check compatible with python 3.6 -> PlotWave in same Main GUI thread
"""

from tkinter import *
from tkinter.ttk import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from pathlib import Path
import os
from glob import glob
import queue
import time
import threading
import sounddevice as sd
import soundfile as sf
import librosa
import sys
import pyttsx3
import sqlite3
import datetime
import hashlib


Path("./audio").mkdir(parents=True, exist_ok=True)
Path("./accent").mkdir(parents=True, exist_ok=True)

def str2md5(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def get_audio_file_names(path='./audio/*.wav'):
    audio_files = glob(path)
    result = []
    for file in audio_files:
        result.append(int(os.path.basename(file).strip('.wav')))
    return result

def get_last_audio_file(path='./audio/*.wav'):
    filenames = get_audio_file_names(path)
    if len(filenames) == 0:
        return ""
    filename = np.array(filenames).max()
    filepath = "./audio/" + str(filename) + ".wav"
    return filepath

def recordAudioStream():
    global statusRecord
    global FS

    if statusRecord == False:
        return
    q = queue.Queue()
    fs = FS
    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    try:
        with sf.SoundFile("./audio/" +  str(round(time.time())) + '.wav', mode='x', samplerate=fs, channels=1) as file:
            with sd.InputStream(samplerate=fs, channels=1, callback=callback):
                while statusRecord:
                    file.write(q.get())

    except KeyboardInterrupt:
        print("Recording finished")

    except Exception as e:
        print("Unknown Error")

def clearAllAudio():
    audios = glob("./audio/*")
    for file in audios:
        os.remove(file)
    accents = glob("./accent/*")
    for file in accents:
        os.remove(file)

def strip_silence_lead(x, frame_length, hop_length):

    # Compute RMSE.
    rmse = librosa.feature.rms(x, frame_length=frame_length, hop_length=hop_length, center=True)
    
    # Identify the first frame index where RMSE exceeds a threshold.
    thresh = 0.01
    frame_index = 0
    while rmse[0][frame_index] < thresh:
        frame_index += 1
        
    # Convert units of frames to samples.
    start_sample_index = librosa.frames_to_samples(frame_index, hop_length=hop_length)
    
    # Return the trimmed signal.
    return start_sample_index

def strip_silence(x, frame_length=512, hop_length=256):
    start_trim = strip_silence_lead(x, frame_length, hop_length)
    end_trim = strip_silence_lead(x[::-1], frame_length, hop_length)
    trim_x = x[start_trim:len(x)-end_trim]
    return trim_x

def add_new_data_to_DB(word):
    word = str2md5(word.lower())
    now = datetime.date.today()
    con = sqlite3.connect("data.db")
    cur = con.cursor()
    select_exist_data = cur.execute("""SELECT Tries FROM learning WHERE Word=(?) AND Date=(?)""", (word,str(now)))
    last_data = select_exist_data.fetchone()
    if last_data == None:
        cur.execute("""INSERT INTO learning VALUES(?,?,?)""",(str(now), word, 1))
        con.commit()
        con.close()
    else:
        tries_new = last_data[0] + 1
        cur.execute("""UPDATE learning SET Tries=(?) WHERE Word=(?) AND Date=(?)""", (tries_new,word,str(now)))
        con.commit()
        con.close()

def show_all_data():
    con = sqlite3.connect("data.db")
    cur = con.cursor()
    for row in cur.execute("""SELECT * FROM learning"""):
        print(row)
    con.commit()
    con.close()

def get_num_tries_of_word(word):
    word = str2md5(word.lower())
    now = datetime.date.today()
    con = sqlite3.connect("data.db")
    cur = con.cursor()
    select_exist_data = cur.execute("""SELECT Tries, Word FROM learning WHERE Word=(?) AND Date=(?)""", (word,str(now)))
    last_data = select_exist_data.fetchone()
    if last_data == None:
        con.commit()
        con.close()
        return 0
    else:
        num = int(last_data[0])
        con.commit()
        con.close()
        return num

def create_DB():
    con = sqlite3.connect("data.db")
    cur = con.cursor()
    cur.execute("""CREATE TABLE learning (Date DATE, Word TINYTEXT PRIMARY KEY, Tries INT)
    """)
    con.commit()
    con.close()

# Clean Audio file - Refresh App
clearAllAudio()
# Start Engine for convert text to speech
engine = pyttsx3.init()

# Create Database if not exists

if os.path.exists("data.db") == False:
    create_DB()

# Start building GUI App
root = Tk()
root.title("Learning Speaking App by Tuan")

# Set speech speed. 100 = 100%, and so on

speed_speech = IntVar()
speed_speech.set(70)
engine.setProperty('rate', 70)

# Configure Style



# Declare command function



def btnRecord():
    global record_Button
    global statusRecord
    global number_of_tries_Label
    global text_input_Text

    text_input = str2md5(text_input_Text.get("1.0", END).strip())
    
    record_Button.grid_forget()

    if statusRecord:
        statusRecord = False
        record_Button = Button(root, text="Record!", command=btnRecord)

    else:
        statusRecord = True
        record_Button = Button(root, text="Recording!", command=btnRecord) 
        th = threading.Thread(target=recordAudioStream)
        th.start()

        add_new_data_to_DB(text_input)

        number_of_tries_Label.grid_forget()
        number_of_tries_Label = Label(root, text="Number of tries: " + str(get_num_tries_of_word(text_input)))
        number_of_tries_Label.grid(row=1,column=0, columnspan=2)

    record_Button.grid(row=2,column=0, sticky=E)

def btnPlayback():
    data, fs = sf.read(get_last_audio_file())
    sd.play(data, fs)
    sd.wait()

def plotWaveSound():
    global text_input_Text
    word = str2md5(text_input_Text.get("1.0", END).strip())
    # Plot wave
    fig = Figure(figsize=(12, 5), dpi=100)

    
    audio_path_file = get_last_audio_file()
    if audio_path_file != "":
    # AUdio Sound Wave
        audio_data, audio_fs = sf.read(audio_path_file)
        audio_data = strip_silence(audio_data)
        fig.add_subplot(211, yticks=np.arange(-1,1.2,0.2), autoscaley_on=False).plot(audio_data)

    # Check if accent file exists, if not, save file
    accent_path_file = "./accent/" + word + ".wav"
    if os.path.exists(word + ".wav") == False:
        engine.save_to_file(word, accent_path_file)
        engine.runAndWait()
    # Accent Soucd Wave
    accent_data, accent_fs = sf.read(accent_path_file)
    accent_data = strip_silence(accent_data)
    fig.add_subplot(212, yticks=np.arange(-1,1.2,0.2), autoscaley_on=False).plot(accent_data)

    canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().grid(row=3, column=0, columnspan=4, sticky=E+W)

def playback_accent_and_sound():
    audio_path_file = get_last_audio_file()
    if audio_path_file != "":
        audio, fs = sf.read(audio_path_file)
        sd.play(audio, fs)
        sd.wait()

def hear_word_new_thread():
    global text_input_Text
    word = text_input_Text.get("1.0", END).strip()
    if word != "":
        engine.say(word)
        engine.runAndWait()

def hear_word():
    th = threading.Thread(target=hear_word_new_thread)
    th.start()

def btnCheck():
    global text_input_Text
    if text_input_Text.get("1.0", END).strip() == "":
        return
    th1 = threading.Thread(target=playback_accent_and_sound)
    # th2 = threading.Thread(target=plotWaveSound)
    th1.start()
    # th2.start()
    plotWaveSound()

def set_speak_speed():
    global speed_speech
    engine.setProperty('rate', speed_speech.get())
# Declare Variable

statusRecord = False
FS = 48000

# Declare elements
text_input_Text = Text(root, width=40, height=5)
hear_word_Button = Button(root, text="Hear It!", command=hear_word)
number_of_tries_Label = Label(root, text="Number of tries show here!")
record_Button = Button(root, text="Record", command=btnRecord)
check_Button = Button(root, text="Check", command=btnCheck)
speed_speech_Button = Button(root, text="Set speed of speech to hear:", command=set_speak_speed)
speed_speech_Entry = Entry(root, textvariable=speed_speech, width=7)

# Bind key -> command

# root.bind("<Control-r>", lambda x: btnRecord())
# text_input_Text.bind("<Control-Enter>", lambda x: hear_word())

# Sort and show elements
text_input_Text.grid(row=0, column=0, sticky=E)
hear_word_Button.grid(row=0, column=1, sticky=W)
speed_speech_Button.grid(row=0,column=2, sticky=E)
speed_speech_Entry.grid(row=0, column=3, sticky=W)
number_of_tries_Label.grid(row=1,column=0, columnspan=2)
record_Button.grid(row=2,column=0, sticky=E)
check_Button.grid(row=2, column=1, sticky=W)


# Plot Wave Example

fig = Figure(figsize=(12, 5), dpi=100)
t = np.arange(0, 3, .01)
fig.add_subplot(211).plot(t, 2 * np.sin(2 * np.pi * t))
fig.add_subplot(212).plot(t, 2 * np.sin(2 * np.pi * t))

canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
canvas.draw()
canvas.get_tk_widget().grid(row=3, column=0, columnspan=4, sticky=E+W)


root.mainloop()