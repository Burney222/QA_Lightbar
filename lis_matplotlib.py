#!c:/Python27/python.exe -u
import Tkinter
import numpy as np
# do this before importing pylab or pyplot
import matplotlib
#matplotlib.use('GtkAgg')
#matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import serial
import sys
import msvcrt
import time
from collections import deque

import atexit

pause = False;

def exit_handler():
    print 'My application is ending!'

def onClick(event):
    global pause
    pause ^= True


atexit.register(exit_handler)

if len(sys.argv) != 2:
    print 'Error! try:'
    print 'python.exe ./lis_matplotlib.py <COMport>'
    print 'or'
    print "./lis_matplotlib.exe <COMport>\n"
    sys.exit(2)
print 'Number of arguments:', len(sys.argv), 'arguments.'
print 'Argument List:', str(sys.argv)

csfont = {'fontname':'Comic Sans MS'}
hfont = {'fontname':'Times New Roman'}
textstr = 'null'
fig = plt.figure(figsize=(16,8),facecolor="white")
ax = plt.axes(xlim=(0, 900), ylim=(0, 3.5))
line, = ax.plot([], [], lw=2)
line.set_antialiased(False) # turn off antialising
ax.grid()
# Remove the plot frame lines. They are unnecessary chartjunk.
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
# Ensure that the axis ticks only show up on the bottom and left of the plot.
# Ticks on the right and top of the plot are generally unnecessary chartjunk.
ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()
# Make sure your axis ticks are large enough to be easily read.
# You don't want your viewers squinting to read your plot.
plt.xticks(range(0, 900, 100), fontsize=16)
plt.yticks(range(0, 4, 1), fontsize=16)
plt.ylabel('Intensity (Volts)', fontsize=20,**csfont)
plt.xlabel('Channel', fontsize=20,**csfont)
# Make the title big enough so it spans the entire plot, but don't make it
# so big that it requires two lines to show.
plt.title("Lightyield Measurement with Arduino/TAOS TSL2014", fontsize=22,**csfont)
boxtext1 = plt.text(0.8, 0.05, "null", size=20, rotation=0.,
         ha="center", va="center", transform=ax.transAxes,
         bbox=dict(boxstyle="round", ec='k', fc='w')
         )
boxtext2 = plt.text(0.8, 0.15, "null", size=20, rotation=0.,
         ha="center", va="center", transform=ax.transAxes,
         bbox=dict(boxstyle="round",ec='k',fc='w')
         )

try:
    ser = serial.Serial(str(sys.argv[1]),115200, timeout=3)
    print("connected to: " + ser.name)

except serial.serialutil.SerialException:
  print 'Error. Device not found on ',str(sys.argv[1])
  sys.exit(2)

readings = []


# initialization function: plot the background of each frame
def init():
    line.set_data([], [])
    boxtext1.set_text('')
    boxtext2.set_text('')
    boxtext1.set_color('none')
    boxtext2.set_color('none')
    return line,boxtext1,boxtext2

# animation function.  This is called sequentially
def animate(i):
    x = list(range(897))
    for j in range(5):
        reading = ser.readline()
        if reading[0]=='0':
            break
    y = reading.split(",")
    #y[895]='0'
    y = list(map(int,y))
    y2= [j / 51.0 for j in y]
    avgtext = str(np.mean(y2))
    variancetext = str(np.std(y2) / np.mean(y2))
    avg = np.mean(y2)
    variance = np.std(y2) / np.mean(y2)
    boxtext1.set_text("mean = "+avgtext[0:6])
    boxtext2.set_text(r"$\sigma$/mean = "+variancetext[0:6])
    line.set_data(x, y2)
    if (avg >= 1.0) and (avg <=3.0):
        boxtext1.set_color('g')
    else:
        boxtext1.set_color('r')
    if (variance <= 0.25):
        boxtext2.set_color('g')
    else:
        boxtext2.set_color('r')
    y3 = deque(y2)
    return line,boxtext1,boxtext2

# call the animator.  blit=True means only re-draw the parts that have changed.
fig.canvas.mpl_connect('button_press_event', onClick)
anim = animation.FuncAnimation(fig, animate, init_func=init,frames=None, interval=200, blit=False,
    repeat=True)
plt.show()

ser.close()
print("Goodbye!\n")
time.sleep(0.5)
