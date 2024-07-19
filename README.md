# FishingAutomation
A Minecraft Bedrock fishing automation program made with Python.

![interface of the program](/images/gui.PNG)

Video or it working: https://youtu.be/2GhL4LyC7fI

# Usage

Install the required libraries for python:
```
pip install -r requirements.txt
```

Install and activate the minecraft resource pack ```fishingResourcePack.mcpack``` for color detection (double click to import it to the game).

After running ```main.py```, press F10 near a lake and the program will start fishing automatically.

## Pyinstaller
You can use ```pyinstaller``` to create a single executable file for the program. First install it by running

```
pip install pyinstaller
```

And then create the executable with

```
pyinstaller --onefile --noconsole main.py
```

The executable will be found inside the dist folder in the current directory.

## Parameters
There are three parameters that can be changed within the program. My instance worked fine with the current default values, but you can modify them if needed.

- Seconds per cycle: This is the delay that each cycle has at the end of its execution (50ms is the default value). A lower value means higher FPS, but this is not really necessary. You can increase this value if for some reason your computer is having trouble.
- Seconds after retracting: This is the time that the program will wait before throwing the hook after just having retracted it.
- Distance for detection: This is the distance from the hook to the head of the trailing water particles from the fish. The greater the value of this parameter, the earlier will the program retract the hook. If you look closely at the preview image, whenever the program detects both the hook (red) and the water particles from the fish (green), a dark blue circle will be drawn. The distance for detection is how close these circles have to be for the program to retract the hook. You might have to adjust this value according to the DPI of your display. You should also take into consideration whether you are going to be played in windowed or fullscreen mode.

## Tips
- Try out the default settings for a while, then modify if needed (changes are not saved).
- For consistent color detection, place torches near or above the water surface where you'll be fishing.
- Isolate or protect your surroundings from possible danger.
- Use hoppers to automatically pick up items once your inventory is full for a better AFK experience.
- Be aware of the creatures near your fishing spot, since bad timing can mean hooking up one of these creatures and the program will not get more instructions to retract the hook (because no water particles from a fish will be detected).
- In my experience, the program works surprisingly well even if its raining, but try to prevent fishing while raining if possible.

## Issues
The program is not tested for double or more monitor setups, so color detection may or may not work properly.
This program was only tested in Windows 10. This should not be a concern anyway, since minecraft bedrock is only available for windows computers at the moment, I believe.

