# Fishing Automation.
# cenfra

# program version
__version__ = "0.1"

import wx
import time
import threading
import pyautogui
import cv2
import ctypes
import logging
import os
import numpy as np
from wx.adv import AboutDialogInfo
from wx.adv import AboutBox
from wx.adv import NotificationMessage
from wx.lib import wordwrap
from pynput import keyboard

# set dpi awareness
ctypes.windll.shcore.SetProcessDpiAwareness(1)

# colors for detecting hook and water particles (using resource pack with new textures)
# red color (hook)
lower1 = np.array((179, 179, 56))
upper1 = np.array((179, 255, 255))
# green color (water particles)
lower2 = np.array((63, 226, 202))
upper2 = np.array((85, 255, 225))

# functions 

# for handling device independent pixels
def dip(*args):
    if len(args) == 1:
        return wx.ScreenDC().FromDIP(wx.Size(args[0], args[0]))[0]
    elif len(args) == 2:
        return wx.ScreenDC().FromDIP(wx.Size(args[0], args[1]))
    else:
        raise ValueError("Exceeded number of arguments.")


# for finding the closest points from the water particles contour and the hook contour (measuring distance)
def find_closest_points(contour1, contour2):
    min_distance = float('inf')
    closest_points = (None, None)

    # iterate through each point in the first contour
    for point1 in contour1:
        point1 = point1[0]
        # iterate through each point in the second contour
        for point2 in contour2:
            point2 = point2[0]
            # calculate euclidean distance between the points
            distance = np.linalg.norm(point1 - point2)
            # update the minimum distance and closest points
            if distance < min_distance:
                min_distance = distance
                closest_points = (point1, point2)

    return closest_points, min_distance


# set up log handler
class WxTextCtrlHandler(logging.Handler):
    def __init__(self, textCtrl):
        super().__init__()
        self.textCtrl = textCtrl

    def emit(self, record):
        msg = self.format(record)
        wx.CallAfter(self.textCtrl.AppendText, msg + '\n')


# main program frame
class MainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Attributes and variables
        self.automationState = False
        self.automationDelaySeconds = 0.05
        self.keyToStartStop = keyboard.Key.f10
        self.threadIsActive = False
        self.imageResolution = (300, 200)
        self.hookIsThrown = False
        self.distanceThatTriggersDetection = 3
        self.delaySecondsAfterRetracting = 1
        
        # setup screenshotting
        self.screen = wx.ScreenDC()
        self.size = self.screen.GetSize()
        self.bmp = wx.Bitmap(self.size[0], self.size[1])
        self.scaledBmp = None 
        
        # initialize interface
        self.init_ui()
        
        # Set up key listener to get key pressed status (to get start and stop key status)
        self.listener = keyboard.Listener(on_press=self.OnPress)
        self.listener.start()
        
        # start main thread
        self.threadIsActive = True
        self.automationThread = threading.Thread(target=self.automationLoop, args=())
        self.automationThread.start()


    def init_ui(self):
        
        # frame attributes
        self.SetTitle(f"Fishing automation v{__version__}")
        self.SetMinClientSize(dip(700, 500))
        self.SetMaxClientSize(dip(700, 500))
        
        # bind events
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        # create main panel
        self.mainPanel = wx.Panel(self)
        
        # crate preview staticbox
        self.staticBoxPreview = wx.StaticBox(self.mainPanel, label="Preview")
        self.staticBoxPreview_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.bmpScreenshot() # save first screenshot
        self.previewImage = wx.StaticBitmap(self.staticBoxPreview, -1, self.scaledBmp, (10, 5), dip(*self.imageResolution))
        self.staticBoxPreview_sizer.AddSpacer(dip(25))
        self.staticBoxPreview_sizer.Add(window=self.previewImage, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM, border=dip(15))
        self.staticBoxPreview.SetSizer(self.staticBoxPreview_sizer)
        
        # create setup staticbox
        self.staticBoxSetup = wx.StaticBox(self.mainPanel, label="Setup")
        
        self.tcSecondsPerCycle = wx.TextCtrl(self.staticBoxSetup, value=str(self.automationDelaySeconds), size=dip(75, -1))
        self.tcSecondsAfterRetracting = wx.TextCtrl(self.staticBoxSetup, value=str(self.delaySecondsAfterRetracting), size=dip(75, -1))
        self.tcDistanceForDetection = wx.TextCtrl(self.staticBoxSetup, value=str(self.distanceThatTriggersDetection), size=dip(75, -1))
        self.stStatus = wx.StaticText(self.staticBoxSetup, label="OFF")
        self.stStatus.SetForegroundColour(wx.RED)
        self.btStartStop = wx.Button(self.staticBoxSetup, label="Start or Stop (F10)")
        self.btStartStop.Bind(wx.EVT_BUTTON, self.checkValuesAndRun)
        
        self.staticBoxSetup_sizer = wx.GridBagSizer(vgap=dip(10))
        self.staticBoxSetup_sizer.Add(window=wx.StaticText(self.staticBoxSetup, label=""), pos=(0, 0), flag=wx.LEFT|wx.TOP, border=dip(13))
        self.staticBoxSetup_sizer.Add(window=wx.StaticText(self.staticBoxSetup, label="Seconds per cycle:"), pos=(1, 0), flag=wx.LEFT|wx.ALIGN_RIGHT, border=dip(10))
        self.staticBoxSetup_sizer.Add(window=wx.StaticText(self.staticBoxSetup, label="Seconds after retracting:"), pos=(2, 0), flag=wx.LEFT|wx.ALIGN_RIGHT, border=dip(10))
        self.staticBoxSetup_sizer.Add(window=wx.StaticText(self.staticBoxSetup, label="Distance for detection:"), pos=(3, 0), flag=wx.LEFT|wx.ALIGN_RIGHT, border=dip(10))
        self.staticBoxSetup_sizer.Add(window=wx.StaticText(self.staticBoxSetup, label="Status:"), pos=(4, 0), flag=wx.LEFT|wx.ALIGN_RIGHT, border=dip(10))
        self.staticBoxSetup_sizer.Add(window=self.tcSecondsPerCycle, pos=(1, 1), flag=wx.ALIGN_LEFT|wx.LEFT, border=dip(15))
        self.staticBoxSetup_sizer.Add(window=self.tcSecondsAfterRetracting, pos=(2, 1), flag=wx.ALIGN_LEFT|wx.LEFT, border=dip(15))
        self.staticBoxSetup_sizer.Add(window=self.tcDistanceForDetection, pos=(3, 1), flag=wx.ALIGN_LEFT|wx.LEFT, border=dip(15))
        self.staticBoxSetup_sizer.Add(window=self.stStatus, pos=(4, 1), flag=wx.ALIGN_LEFT|wx.LEFT, border=dip(15))
        self.staticBoxSetup_sizer.Add(window=self.btStartStop, pos=(5, 0), span=(1, 2), flag=wx.LEFT|wx.RIGHT|wx.EXPAND, border=dip(10))
        self.staticBoxSetup_sizer.AddGrowableCol(1, 1)
        self.staticBoxSetup.SetSizer(self.staticBoxSetup_sizer)
        
        # create logging staticbox
        self.staticBoxLogging = wx.StaticBox(self.mainPanel, label="Log")
        self.loggingBox = wx.TextCtrl(self.staticBoxLogging, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.staticBoxLogging_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.staticBoxLogging_sizer.AddSpacer(dip(25))
        self.staticBoxLogging_sizer.Add(self.loggingBox, proportion=1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=dip(8))
        self.staticBoxLogging.SetSizer(self.staticBoxLogging_sizer)
        self.setupLogging()
        
        # create sizer and add static boxes        
        self.mainSizer = wx.GridBagSizer()
        self.mainSizer.Add(window=self.staticBoxPreview, pos=(0, 0), flag=wx.TOP|wx.LEFT, border=dip(10))
        self.mainSizer.Add(window=self.staticBoxSetup, pos=(0, 1), flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=dip(10))
        self.mainSizer.Add(window=self.staticBoxLogging, pos=(1, 0), span=(1, 2), flag=wx.EXPAND|wx.ALL, border=dip(10))
        
        # set up growable columns
        self.mainSizer.AddGrowableCol(1, 1)
        self.mainSizer.AddGrowableRow(1, 1)
        self.mainPanel.SetSizer(self.mainSizer)
        
        # menubar
        self.menuBar = wx.MenuBar()
        helpMenu = wx.Menu()
        aboutItem = helpMenu.Append(id=100, item="About", helpString="About this program")
        self.menuBar.Append(helpMenu, "Help")
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)
        self.SetMenuBar(self.menuBar)
        
        # statusbar
        self.statusBar = self.CreateStatusBar()
        self.statusBar.SetStatusText("")


    def setupLogging(self):
        handler = WxTextCtrlHandler(self.loggingBox)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # test
        """
        logging.debug('This is a debug message')
        logging.info('This is an info message')
        logging.warning('This is a warning message')
        logging.error('This is an error message')
        logging.critical('This is a critical message')
        """


    def bmpScreenshot(self):
        # places screenshot in self.bmp
        self.mem = wx.MemoryDC(self.bmp)
        self.mem.Blit(0, 0, self.size[0], self.size[1], self.screen, 0, 0)
        del self.mem
        # scales down screenshot
        self.scaledBmp = self.bmp.ConvertToImage()
        self.scaledBmp = self.scaledBmp.Scale(self.imageResolution[0], self.imageResolution[1])
        self.scaledBmp = self.scaledBmp.ConvertToBitmap()


    def checkValuesAndRun(self, event=None):
        # update values
        secondsPerCycle = self.tcSecondsPerCycle.GetValue()
        distanceDetection = self.tcDistanceForDetection.GetValue()
        delaySeconds = self.tcSecondsAfterRetracting.GetValue()
        
        # check if values are valid
        if secondsPerCycle.strip() == "" or secondsPerCycle == "0":
            logging.error("Enter a valid value for seconds per cycle.")
            return
        if delaySeconds.strip() == "" or delaySeconds == "0":
            logging.error("Enter a valid value for seconds after retracting.")
            return
        if distanceDetection.strip() == "" or distanceDetection == "0":
            logging.error("Enter a valid value for distance detection.")
            return
        
        self.automationDelaySeconds = float(secondsPerCycle)
        self.distanceThatTriggersDetection = float(distanceDetection)
        self.delaySecondsAfterRetracting = float(delaySeconds)
        logging.info("Updated values correctly.")
        
        
        # invert automation state
        self.automationState = not self.automationState
        logging.info(f"Automation state: {self.automationState}")
        
        # show status as notification
        status = "ON" if self.automationState else "OFF"
        
        # status statictext
        if self.automationState:
            self.stStatus.SetForegroundColour(wx.Colour(69, 146, 1))
        else:
            self.stStatus.SetForegroundColour(wx.RED)
        self.stStatus.SetLabel(status)
        
        msg = NotificationMessage(parent=self, title="Fishing Automation", message=f"Fishing Status: {status}")
        msg.Show()


    def OnPress(self, key):
        if (key==self.keyToStartStop):
            self.checkValuesAndRun()


    def automationLoop(self):
        
        while (self.threadIsActive):
            
            if (self.automationState):
                
                # save screenshot to self.bmp and self.scaledBmp
                self.bmpScreenshot()

                # convert screenshot bitmap to numpy array (image)
                # scaledBmp and reshape values must be same resolution
                img = self.scaledBmp.ConvertToImage()
                buf = img.GetDataBuffer()
                a = np.frombuffer(buf, dtype=np.uint8)
                # create valid image array
                self.image = np.reshape(a, (self.imageResolution[1], self.imageResolution[0],3))
                # copy original image (for drawing and displaying in rgb)
                self.imageOriginal = self.image.copy()

                # change color space to HSV
                self.image = cv2.cvtColor(self.image, cv2.COLOR_RGB2HSV)
                # get masks
                maskRed = cv2.inRange(self.image, lower1, upper1)
                maskGreen = cv2.inRange(self.image, lower2, upper2)
                # get contours
                contoursRed, _ = cv2.findContours(maskRed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contoursGreen, _ = cv2.findContours(maskGreen, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                # get largest contours
                maxRed = max(contoursRed, key=cv2.contourArea) if len(contoursRed) != 0 else []
                maxGreen = max(contoursGreen, key=cv2.contourArea) if len(contoursGreen) != 0 else []
                
                # if there are contours for both red and green objects
                if (len(maxRed) != 0) and (len(maxGreen) != 0):
                    # get closest point between contours
                    closest, distance = find_closest_points(maxRed, maxGreen)
                    # draw closest points
                    cv2.circle(self.imageOriginal, closest[0], 5, (0, 0, 150), -1)
                    cv2.circle(self.imageOriginal, closest[1], 5, (0, 0, 150), -1)
                    # if the distance betwween the two contours is between range of detection
                    if distance > 0 and distance <self.distanceThatTriggersDetection:
                        # right click (retract hook)
                        pyautogui.click(button='right')
                        logging.info(f"Caught fish.")
                        self.hookIsThrown = False
                        logging.info(f"Hook is retracted.")
                        # delay because next lines will throw hook again
                        time.sleep(self.delaySecondsAfterRetracting)

                # throw hook after it was retracted
                if not self.hookIsThrown:
                    pyautogui.click(button='right')
                    self.hookIsThrown = True
                    logging.info(f"Hook is thrown.")
                    
                self.previewImage.SetBitmap(wx.Bitmap.FromBuffer(self.imageResolution[0], self.imageResolution[1], self.imageOriginal))

                
                time.sleep(self.automationDelaySeconds)
        
        return     


    def OnAbout(self, event):
        info = AboutDialogInfo()
        info.Name = "Fishing Automation"
        info.Version = f"{__version__}"
        info.Copyright = "ceniceros"
        info.Description = wordwrap.wordwrap("A fishing automation tool for Minecraft Bedrock.", 400, wx.ClientDC(self))
        #info.Developers = ["cenfra"]
        AboutBox(info)


    def OnClose(self, event):
        logging.info(f"Exiting...")
        # unset thread variable
        self.threadIsActive = False
        # wait for thread to stop
        self.automationThread.join()
        # stop key listener
        self.listener.stop()
        # destroy frame
        self.Destroy()
        # completely exit program
        os._exit(1)



# main application loop
app = wx.App()
instance = MainFrame(parent=None)
instance.Show()
app.MainLoop()
