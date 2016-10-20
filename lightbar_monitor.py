#!c:/Python27/python.exe -u
import Tkinter
import sys
import serial
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import atexit
import numpy as np

# Global variable that stores information about if there was a click
clicked = False

# Cleanup function at exit of the program
def exit_handler():
    print "\nExiting {} ...".format(sys.argv[0])
    if 'ser' in globals():
        print "Closing serial connection to {} ...".format(ser.name)
        ser.close()

atexit.register(exit_handler)


# Check if the COM port is correctly given as the argument
if len(sys.argv) != 2:
    print "Error! One argument expected that defines the COM port of the Arduino"
    print "\nExamples:\nWindows: python.exe ./{} <COMport>".format(sys.argv[0])
    print "Mac/Linux: python {} <COMport>".format(sys.argv[0])
    sys.exit(2)

# Try to connect to the Arduino
try:
    ser = serial.Serial(sys.argv[1], 115200, timeout=3)
    print "Successfully connected to Arduino on {}".format(ser.name)
except:
    print "Error! Arduino not found on {}".format(sys.argv[1])
    sys.exit(2)


# Define the appearance of the plot
fig = plt.figure(figsize=(16,8), facecolor = "white")
permline, = plt.plot([], [], linewidth=2, color="r")    #Line that is triggered on click (for ref.)
line, = plt.plot([], [], linewidth=2, color="b")
plt.plot([0,895], [3.63, 3.63], "k--")
plt.ylabel("Intensity (Volts)", fontsize=20)
plt.xlabel("Channel", fontsize=20)
plt.title("Lightyield Measurement with Arduino/TAOS TSL2014", fontsize=22)
plt.xlim(0, 895)
plt.xticks(range(0, 895, 100), fontsize=16)
plt.ylim(0, 5)
plt.yticks(range(0, 5, 1), fontsize=16)
plt.grid()  #Plot grid

# Boxes that store information about the mean and std across the different channels
box1 = plt.text(0.75, 0.9, "no data", size=20, transform=plt.gca().transAxes,
        bbox=dict(boxstyle="round", ec='b', fc='w', lw="2"))
box2 = plt.text(0.75, 0.8, "no data", size=20, transform=plt.gca().transAxes,
        bbox=dict(boxstyle="round",ec='b',fc='w', lw="2"))

box_perm1 = plt.text(0.45, 0.9, "null", size=20, transform=plt.gca().transAxes,
        bbox=dict(boxstyle="round", ec='r', fc='w', lw="2"))
box_perm2 = plt.text(0.45, 0.9, "Click to freeze\ncurrent measurement!", size=20,
        transform=plt.gca().transAxes, bbox=dict(boxstyle="round", ec='r', fc='w', lw="2"))

# Function that is called sequentially and updates the plot
def update_line(iteration, line, permline, box1, box2, box_perm1, box_perm2):

    x = list(range(896))
    #Try 5 times to get a correct serial line (i.e. data from all 896 channels)
    for i in range(5):
        reading = ser.readline()
        #A correct line starts with an exclamation mark!
        if len(reading) > 0 and reading[0] == "!": # Remove exclamation mark and go to next stage
            reading = reading[1:]
            break

    try:
        #Transform string into list of integers for each channel
        y = list(map(int, reading.split(",")))
    except:
        print "Error! Could not convert serial input string into list."
        if reading == "":
            reading = "<empty>"
        print "Serial input: {}".format(reading)
        print "Try reconnecting the Arduino."
        sys.exit(1)

    y = [val / 51.0 for val in y]   #Downscaling
    line.set_data(x, y)

    #Update box texts
    avg = np.mean(y)
    rel_std = np.std(y) / avg if avg != 0 else "null"
    box1.set_text("mean = {:.5}".format(avg))
    box2.set_text(r"$\sigma$/mean = {:.5}".format(rel_std))
    if avg >= 1. and avg <= 3.:
        box1.set_color("g")
    else:
        box1.set_color("r")
    if rel_std <= 0.25:
        box2.set_color("g")
    else:
        box2.set_color("r")

    #Update permline and corresponding boxes if there was a click
    global clicked
    if clicked:
        permline.set_data(x, y)     #Set the permanent line to the current data
        box_perm1.set_text("mean = {:.5}".format(avg))
        box_perm2.set_text(r"$\sigma$/mean = {:.5}".format(rel_std))
        box_perm2.set_y(0.8)
        if avg >= 1. and avg <= 3.:
            box_perm1.set_color("g")
        else:
            box_perm1.set_color("r")
        if rel_std <= 0.25:
            box_perm2.set_color("g")
        else:
            box_perm2.set_color("r")

        clicked = False #Change click to false again

    return line, permline, box1, box2, box_perm1, box_perm2

# Define behaviour when clicking
def onClick(event):
    global clicked
    clicked = True



fig.canvas.mpl_connect('button_press_event', onClick)
anim = animation.FuncAnimation(fig, update_line, fargs=[line, permline, box1, box2, box_perm1,
                    box_perm2], interval=200, blit=False, repeat=True, frames=None)
plt.show()
