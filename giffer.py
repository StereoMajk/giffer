import board
import displayio
import terminalio
import busio
import gifio
import time
import os
import gc
import random
import sdcardio
import storage
from adafruit_display_text import label
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer


# Starting in CircuitPython 9.x fourwire will be a seperate internal library
# rather than a component of the displayio library
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

from adafruit_st7789 import ST7789

btn = DigitalInOut(board.GP8)
btn.direction = Direction.INPUT
btn.pull = Pull.UP
switch = Debouncer(btn)


# Get a dictionary of GIF filenames at the passed base directory
def get_files(base):
    allfiles = os.listdir(base)
    file_names = []
    for _, filetext in enumerate(allfiles):
        if not filetext.startswith("."):
            if filetext not in ('boot_out.txt', 'System Volume Information'):
                if filetext.endswith(".gif"):
                    file_names.append(filetext)
    return file_names

displayio.release_displays()

spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)
while not spi.try_lock():
    pass
spi.configure(baudrate=24000000) # Configure SPI for 24MHz
spi.unlock()
tft_cs = board.GP5
tft_dc = board.GP6

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP9)

display = ST7789(display_bus, width=320, height=172, colstart=34, rotation=270)
root = displayio.Group(scale=1,x=0,y=0)
splash = displayio.Group(scale=3,x=35, y=60)
text_group = displayio.Group(scale=2,x=35, y=44)
display.root_group = root

files = get_files("gifs")
click_count = 0
font = terminalio.FONT
color = 0xFFFFFF
text_area = label.Label(font, text=" "*10, color=color)
text_group.append(text_area)
root.insert(0,splash)
root.insert(1,text_group)
while True:
    switch.update()
    
    selected_gif = random.randint(0,len(files)-1)
    try:
        odg = gifio.OnDiskGif("gifs/"+files[selected_gif])
    except ValueError:
        continue
    start = time.monotonic()
    next_delay = odg.next_frame() # Load the first frame
    end = time.monotonic()
    overhead = end - start
    display.root_group = root
    face = displayio.TileGrid(
        odg.bitmap,
        pixel_shader=displayio.ColorConverter(
            input_colorspace=displayio.Colorspace.RGB565_SWAPPED
        ),
    )
    splash.insert(0,face);
    
    current_display_time = start = time.monotonic()

    while True:
        switch.update()
        if switch.rose:
            text_area.text = str(click_count)
            click_count+=1
            break
        #switch gif after 20 seconds
        if time.monotonic() > current_display_time + 20:
            break
        #calculate delay between frames
        if time.monotonic() > start + next_delay - overhead:
            start = time.monotonic()
            next_delay = odg.next_frame()
            end = time.monotonic()
            overhead = end - start
            start = time.monotonic()
        display.refresh()

    del splash[0]

    odg.deinit()
    odg = None
    gc.collect()
