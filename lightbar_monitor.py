#!c:/Python27/python.exe -u
import Tkinter
import sys
import serial
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backend_bases import FigureCanvasBase
import atexit
import numpy as np
from os.path import splitext

#Modify the print_figure method in FigureCanvasBase to also save the raw data in .csv-file
#when using the save button in the graphical user interface
print_figure = FigureCanvasBase.print_figure
def print_figure_new(self, filename, *args, **kwargs):
    #Additionally save the raw data as .csv
    csvfilename = splitext(filename)[0] + ".csv"
    x, y1 = line.get_data() #blue line
    xcheck, y2 = permline.get_data() #red line
    if not xcheck:  #xcheck is empty
        y2 = np.zeros(len(y1))
    elif x != xcheck:
        print "Something went wrong when saving the raw data in {}".format(csvfilename)
        sys.exit(1)
    np.savetxt(csvfilename, np.asarray([x,y1,y2]).transpose(), fmt=["%i", "%.8f", "%.8f"],
               header="Channel, Intensity (blue line) [V], Intensity (red line, if applicable) [V]")
    print "Saving raw data and plot to {} and {}".format(csvfilename, filename)
    #run the normal method
    return print_figure(self, filename, *args, **kwargs)

FigureCanvasBase.print_figure = print_figure_new

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
plt.plot([0,895], [3.63, 3.63], "k--")      #Saturation level
plt.text(0.01, 0.735, "Saturation level", size=13, transform=plt.gca().transAxes)
plt.ylabel("Intensity (Volts)", fontsize=20)
plt.xlabel("Channel", fontsize=20)
plt.title("Lightyield Measurement with Arduino/TAOS TSL2014", fontsize=22)
plt.xlim(0, 895)
plt.xticks(range(0, 895, 100), fontsize=16)
plt.ylim(0, 5)
plt.yticks(range(0, 5, 1), fontsize=16)
plt.grid()  #Plot grid

# Boxes that store information about the mean and std across the different channels
parameterbox = plt.text(0.01, 0.9, "no data", size=20, transform=plt.gca().transAxes,
        bbox=dict(boxstyle="round", ec='k', fc='w', lw="1"))   #LED brightness and integration time
box1 = plt.text(0.75, 0.9, "no data", size=20, transform=plt.gca().transAxes,
        bbox=dict(boxstyle="round", ec='b', fc='w', lw="2"))
box2 = plt.text(0.75, 0.8, "no data", size=20, transform=plt.gca().transAxes,
        bbox=dict(boxstyle="round",ec='b',fc='w', lw="2"))

box_perm1 = plt.text(0.45, 0.9, "null", size=20, transform=plt.gca().transAxes,
        bbox=dict(boxstyle="round", ec='r', fc='w', lw="2"))
box_perm2 = plt.text(0.45, 0.9, "Click to freeze\ncurrent measurement!", size=20,
        transform=plt.gca().transAxes, bbox=dict(boxstyle="round", ec='r', fc='w', lw="2"))

#Markers to indicate the mean
marker_blue, = plt.plot(-1000, 0.0, "b<", ms=10, clip_on=False)
marker_red, = plt.plot(-1000, 0.0, "r<", ms=10, clip_on=False)
plt.text(1.02, 0.5, "Mean values", size=20, transform=plt.gca().transAxes, rotation=270)


# Function that is called sequentially and updates the plot
def update_line(iteration, line, permline, box1, box2, box_perm1, box_perm2, parameterbox,
                marker_blue, marker_red):

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
        values, params = reading.split("|")
        ledbrightness, integrationtime  = map(int, params.split(","))
        y = list(map(int, values.split(",")))
    except:
        print "Error! Could not convert serial input string into list."
        if reading == "":
            reading = "<empty>"
        print "Serial input: {}".format(reading)
        print "Try reconnecting the Arduino."
        sys.exit(1)

    parameterbox.set_text("LED brightness level: {:>4}\nIntegration time (ms): {:>3}".format(
                         ledbrightness, integrationtime))
    y = [val / 51.0 for val in y]   #Downscaling
    line.set_data(x, y)

    #Update box texts and markers
    avg = np.mean(y)
    marker_blue.set_data(900, avg)
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
        marker_red.set_data(900, avg)
        if avg >= 1. and avg <= 3.:
            box_perm1.set_color("g")
        else:
            box_perm1.set_color("r")
        if rel_std <= 0.25:
            box_perm2.set_color("g")
        else:
            box_perm2.set_color("r")

        clicked = False #Change click to false again

    return line, permline, box1, box2, box_perm1, box_perm2, parameterbox, marker_blue, marker_red

# Define behaviour when clicking
def onClick(event):
    global clicked
    clicked = True



fig.canvas.mpl_connect('button_press_event', onClick)
anim = animation.FuncAnimation(fig, update_line, fargs=[line, permline, box1, box2, box_perm1,
                    box_perm2, parameterbox, marker_blue, marker_red], interval=200, blit=False,
                    repeat=True, frames=None)
plt.show()
