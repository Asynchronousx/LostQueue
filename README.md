# LostQueue
A simple overlay for LostArk that shows information about your queue status and time left while tabbed out of the game.<br>

<p align="center">
  <img src="https://preview.redd.it/syb4jtng0uj81.png?width=632&format=png&auto=webp&s=b0d612c0958b1041729f64324df068a58bd101bf" width="512">
</p>

# Overview 
Since we currently do not have any APIs from the game itself, the pipeline implemented is pretty much this: Extracting and processing a frame through win32 libraries, then manipulating the output with opencv to feed the resulting image into Tesseract (OCR) that will perform an Image-To-Text conversion and return our actual queue time. All of that is  implemented into a GUI made from scratch with PyQt5. 

# Usage
The usage is pretty straightforward and could be done in two ways:

## From Release 
Download the .exe file from the release section ([here](https://github.com/Asynchronousx/LostQueue/releases)) and follow this steps: 
- Open the game with your desired resolution: actually supported: 720p, 1080p, 1440p, 2160p BORDERLESS!
- Queue into a server
- Alt+Tab and open the .exe file to start the overlay 

## From Scratch 
Also, the process is pretty simple too: 
- Git Clone
- change directory into the cloned folder 
- python LostQueue.py

NOTE: Be sure to have installed Tesseract in your env and modify the `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'` in `lautils.py` into your actual path to Tesseract

# Requirements
To run those file from scratch you'll need: 
- PyTesseract
- PyQt5
- Numpy
- OpenCV 
- PIL
- win32ui, win32gui, win32com
- pyautogui
- playsound

# Known Problems
- When Tesseract doesn't recognize well the first digit at start, better to restart the overlay
- The game actually needs to run only in Borderless mode (Windowed is not supported). 
- Used playsound to run an audio when logged in but strangely dont work 
- Sometimes the overlay crashes due to some strange logic cases i didn't manage to fix (rarely happens)
- THE EXE IS 144MB and wont embed any external asset wtf pyinstaller lmao?!
