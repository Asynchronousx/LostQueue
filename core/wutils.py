# Class that takes care of initializing processes windows ID and screnshotting.
import win32ui
import win32gui
import win32com.client

from ctypes import windll
from PIL import ImageGrab
from PIL import Image


class WindowsManager():

    def __init__(self):

        # Initialize process list and populate it with the custom function
        self.plist = []
        self.__acquire_processes_ID()

    def __acquire_processes_ID(self):

        # Defining lambda function that append the process pid and the
        # windows name to the process list of the class
        l = lambda hwnd, list: list.append((hwnd, win32gui.GetWindowText(hwnd)))

        # Using win32guo to get the process list
        win32gui.EnumWindows(l, self.plist)

    def get_process_ID(self, name):

        # Getting the wanted process by analyzing the plist built
        # at init
        process_info = [(p, n) for (p, n) in self.plist if name in n.lower()]

        # Handle error: if no process with the given name is found, return None
        # both for name and hwnd
        if len(process_info) == 0:
            return None, None

        # return the process hwnd and name
        return process_info[0][0], process_info[0][1]

    def get_process_screensize(self, name):

        # Get the process id based on the name
        hwnd, _ = self.get_process_ID(name)

        # Handle error: if no process id with the given name is found, return None
        # for w,h
        if not hwnd:
            return None, None

        # Set the correct DPI for the process
        windll.user32.SetProcessDPIAware()

        # Get windows rectangle coordinate
        left, top, right, bot = win32gui.GetClientRect(hwnd)
        w = right - left
        h = bot - top

        # Return width and height of the process
        return (w,h)

    def get_process_snap(self, name):

        # Get process info based on name
        hwnd, _ = self.get_process_ID(name)

        # Handle error: if no process with the given name is found, return None
        # for image, w, h
        if not hwnd:
            return None, None, None

        # Get w and h of the process
        w, h = self.get_process_screensize(name)
        
        # Process window in background
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # Create bitmap from selected windows
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        # Change the line below depending on whether you want the whole window
        # or just the client area.
        #result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 1)
        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)

        # clean objects
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        # Return the converted process image alongside with his resolution info
        return im, w, h
