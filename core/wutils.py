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
        process = [(p, n) for (p, n) in self.plist if name in n.lower()]
        return process

    def get_process_screen(self, name):

        # Get process info based on name
        process_info = self.get_process_ID(name)

        # Handle error: if no process with the given name is found, return None
        if len(process_info) == 0:
            return None, None, None

        # Extract the hwnd from the tuple
        hwnd = process_info[0][0]

        # Set the correct DPI for the process
        windll.user32.SetProcessDPIAware()

        # Get windows rectangle coordinate
        left, top, right, bot = win32gui.GetClientRect(hwnd)
        w = right - left
        h = bot - top

        # TODO: CHECK SCREEN CONSTRAINT!!!

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
