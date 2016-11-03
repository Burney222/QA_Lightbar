#!c:/Python27/python.exe -u
from __future__ import division

import Tkinter
import sys
import serial
import warnings
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backend_bases import FigureCanvasBase
import atexit
import numpy as np
from os.path import splitext

# Global variables that stores information about if there was a mouse click or key press
clicked = False
pressed = False

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


# Cleanup function at exit of the program
def exit_handler():
    print "\nExiting {} ...".format(sys.argv[0])
    if 'ser' in globals():
        print "Closing serial connection to {} ...".format(ser.name)
        ser.close()

# Function that is called sequentially and updates the plot
def update_line(iteration, line, permline, box1, box2, box_perm1, box_perm2, parameterbox,
                marker_blue, marker_red, smearing_text):

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

    parameterbox.set_text("LED brightness level (Ref: 10): {:>3}\nIntegration time/ms  (Ref: 80): {:>3}".format(
                         ledbrightness, integrationtime))
    y = [val / 51.0 for val in y]   #Downscaling

    #Smear data when button was pressed
    global pressed
    if pressed:
        y = smear_data(y, 201)
        smearing_text.set_text("SMEARED!")
        smearing_text.set_x(405)
    else:
        smearing_text.set_text("Press keyboard button to smear data!")
        smearing_text.set_x(250)

    line.set_data(x, y)

    #Update box texts and markers
    avg = np.mean(y)
    marker_blue.set_data(900, avg)
    rel_std = np.std(y) / avg if avg != 0 else "null"
    box1.set_text("mean = {:.5}".format(avg))
    box2.set_text(r"$\sigma$/mean = {:.5}".format(rel_std))
    if avg >= 1.3:
        box1.set_color("g")
    elif avg >= 1.2:
        box1.set_color("orange")
    else:
        box1.set_color("r")
    if rel_std <= 0.4:
        box2.set_color("g")
    elif rel_std <= 0.5:
        box2.set_color("orange")
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
        box_perm1.set_color(box1.get_color())
        box_perm2.set_color(box2.get_color())

        clicked = False #Change click to false again

    #return line, permline, box1, box2, box_perm1, box_perm2, parameterbox, marker_blue, marker_red, smearing_text

# Define behaviour when clicking
def onClick(event):
    global clicked
    clicked = True

# Define behaviour when clicking
def onPress(event):
    global pressed
    pressed = not pressed


def smear_data(data, n_channels=1, channel_weights=None):
    """Function that performs artificial smearing of the data.

    Parameters
    ----------
    data: list, array, tuple etc.
        Input data that is supposed to get smeared. For the TAOS TSL2014 it needs to be a
        list/array/tuple of length 896.

    n_channels: int or list/array/tuple with weights, optional (default=1)
        Channels to be taken into account. If provided with an integer number take this number of
        neighbouring channels for the smearing.
        Neighbouring channels are taken both to the left and right of the middle channel. n_channels
        needs to be an odd number that is interpreted as including the middle channel. The default=1
        corresponds to no smearing.

    channel_weights: list, array, tuple etc., optional (default=None)
        If provided, channel_weights must be of length=n_channels and are interpreted as the weights
        for calculating the weighted arithmetic mean. Weights are not allowed to be negative and
        will be normalized if necessary. The default=None corresponds to the arithmetic mean.

    Returns
    -------
    smeared_data: list, array, tuple etc.
        Smeared data list/array/tuple with the same length as the input data.
    """
    #Consistency checks
    if n_channels < 1:
        raise SystemExit("Number of channels must be greater-equal than 1.")
    if n_channels % 2 != 1:
        raise SystemExit("Number of channels must be an odd number.")
    if channel_weights and len(channel_weights) != n_channels:
        raise SystemExit("Provided channel weights does not match number of channels")
    if channel_weights:
        for weight in channel_weights:
            if weight < 0:
                raise SystemExit("Channel weights must be greater than 0.")
    if not channel_weights:
        channel_weights = np.ones(n_channels)/n_channels
    elif np.sum(channel_weights) != 1:
        print "Warning: Channel weights not normalised - normalising them..."
        channel_weights = np.asarray(channel_weights)/np.sum(channel_weights)

    #Create new artificial data array with extra zeros in the beginning and at the end to handle
    #the channels at the borders
    extended_data = np.array(data)
    extended_data = np.insert(extended_data, 0, np.zeros(n_channels//2))
    extended_data = np.append(extended_data, np.zeros(n_channels//2))

    #Create output data array
    smeared_data = np.zeros(len(data))
    smeared_data.fill(-1)   #default value

    #Create the individual smeared entries
    for idx in range(len(data)):
        idx_ext = idx+n_channels//2  #Corresponding entry in the extended_data array
        #Calculate limits for the slicing of the array
        lower_limit = idx_ext-n_channels//2
        upper_limit = idx_ext+n_channels//2+1
        smeared_data[idx] = np.dot(extended_data[lower_limit:upper_limit], channel_weights)

    return smeared_data











if __name__ == "__main__":
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
    plt.plot([0,895], [1, 1], "k--")      #Lower level
    plt.text(0.01, 0.735, "Saturation level", size=13, transform=plt.gca().transAxes)
    smearing_text = plt.text(250, 0.1, "Press keyboard button to smear data!", size=20)
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
    box_perm2 = plt.text(0.45, 0.9, "Mouse click to freeze\ncurrent measurement!", size=20,
            transform=plt.gca().transAxes, bbox=dict(boxstyle="round", ec='r', fc='w', lw="2"))

    #Markers to indicate the mean
    marker_blue, = plt.plot(-1000, 0.0, "b<", ms=10, clip_on=False)
    marker_red, = plt.plot(-1000, 0.0, "r<", ms=10, clip_on=False)
    plt.text(1.02, 0.5, "Mean values", size=20, transform=plt.gca().transAxes, rotation=270)

    fig.canvas.mpl_connect('button_press_event', onClick)   #Mouse button click
    fig.canvas.mpl_connect('key_press_event', onPress)      #Key button press

    anim = animation.FuncAnimation(fig, update_line, fargs=[line, permline, box1, box2, box_perm1,
                        box_perm2, parameterbox, marker_blue, marker_red, smearing_text],
                        interval=200, blit=False, repeat=True, frames=None)
    plt.show()
