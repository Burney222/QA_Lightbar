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
from matplotlib.patches import FancyBboxPatch
matplotlib.rcdefaults() #Use default matplotlib parameters for portability reasons
import atexit
import numpy as np
from os.path import splitext
import argparse

# Global variables that store information about if there was a mouse click or key press
clicked = False
pressed = False
verbose = False
y_limit = 4
n_parts = 4  #Number of parts for calculating the median uniformity
n_remove_channels = 32   #Remove this amount of channels on both edges! (inactive area)

# Limits
mean_green = 0.5
mean_orange = 0.4

rel_std_green = 0.4
rel_std_orange = 0.45

uniform_green = 0.4
uniform_orange = 0.36


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
        y2 -= 1
    elif x != xcheck:
        print "Something went wrong when saving the raw data in {}".format(csvfilename)
        sys.exit(1)
    np.savetxt(csvfilename, np.asarray([x,y1,y2]).transpose(), fmt=["%i", "%.8f", "%.8f"],
               header="Blue curve: LED brightness = {0}, Integration time = {1}\n"
                      "Red curve: LED brightness = {2}, Integration time = {3} (if applicable)\n"
                      "Channel, Intensity (blue line) [V], Intensity (red line, if applicable) [V]"
                      .format(blue_led, blue_int, red_led, red_int))

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
def update_line(iteration, line, permline, blue_mean, blue_std, blue_uniformity, red_mean, red_std,
                red_uniformity, parameterbox, marker_blue, marker_red, smearing_text, median_lines):

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
        global blue_led, blue_int
        blue_led, blue_int  = map(int, params.split(","))
        y = list(map(int, values.split(",")))
    except:
        print "Error! Could not convert serial input string into list."
        if reading == "":
            reading = "<empty>"
        print "Serial input: {}".format(reading)
        print "Try reconnecting the Arduino."
        sys.exit(1)

    parameterbox.set_text("LED brightness level (Ref:   5): {:>3}\nIntegration time/ms  (Ref: 50): {:>3}".format(
                         blue_led, blue_int))
    y = [val / 51.0 for val in y]   #Downscaling

    #In VERBOSE mode: Smear data when button was pressed
    if verbose:
        global pressed
        if pressed:
            n_channels = 801
            channel_numbers = np.asarray(range(n_channels)) - n_channels//2 #symmetric around zero
            #Different models (comment out the one that you want)
            #channel_weights = channel_weight_model(channel_numbers, (n_channels-1)/6)
            channel_weights = cos_weight_model(channel_numbers)
            #channel_weights = gaussian_weight_model(channel_numbers)
            for i, weight in enumerate(channel_weights):
                if weight < 0:
                    channel_weights[i] = 0
            channel_weights = channel_weights/np.sum(channel_weights)
            y = smear_data(y, n_channels, channel_weights)
            smearing_text.set_text("SMEARED!")
        else:
            smearing_text.set_text("Press keyboard button\nto smear data!")

    #Plot the data!
    line.set_data(x, y)

    #Values for the calculation are without the inactive area!
    y_calc = y[n_remove_channels:-n_remove_channels]
    #Update box texts and markers
    avg = np.mean(y_calc)
    marker_blue.set_data(900, avg)
    rel_std = np.std(y_calc) / avg if avg != 0 else "null"
    uniformity = median_uniformity(y_calc, n_parts=n_parts)
    blue_mean.set_text(r"mean$\,$     = {:.5}".format(avg))
    blue_std.set_text(r"$\sigma$/mean $\,$ = {:.5}".format(rel_std))
    blue_uniformity.set_text("uniform. = {:.5}".format(uniformity))

    #Mean color
    if avg >= mean_green:
        blue_mean.set_color("g")
    elif avg >= mean_orange:
        blue_mean.set_color("orange")
    else:
        blue_mean.set_color("r")

    #Rel. std
    if rel_std <= rel_std_green:
        blue_std.set_color("g")
    elif rel_std <= rel_std_orange:
        blue_std.set_color("orange")
    else:
        blue_std.set_color("r")

    #Median uniformity
    if uniformity >= uniform_green:
        blue_uniformity.set_color("g")
    elif uniformity >= uniform_orange:
        blue_uniformity.set_color("orange")
    else:
        blue_uniformity.set_color("r")

    #In VERBOSE mode: Update permline and corresponding boxes if there was a click
    if verbose:
        global clicked
        if clicked:
            permline.set_data(x, y)     #Set the permanent line to the current data
            red_mean.set_text(blue_mean.get_text())
            red_std.set_text(blue_std.get_text())
            red_uniformity.set_text(blue_uniformity.get_text())
            marker_red.set_data(900, avg)
            red_mean.set_color(blue_mean.get_color())
            red_std.set_color(blue_std.get_color())
            red_uniformity.set_color(blue_uniformity.get_color())
            global red_led, red_int
            red_led = blue_led
            red_int = blue_int

            clicked = False #Change click to false again


        #Plot the medians which are used for calculalating the median uniformity
        medians = get_medians(np.asarray(y_calc), n_parts)
        ch_groups = np.split(np.asarray(range(n_remove_channels, len(y)-n_remove_channels)),n_parts)
        for i in range(len(medians)):
            median_lines[i].set_data([ch_groups[i][0], ch_groups[i][-1]], [medians[i], medians[i]])

    #Adjust the y axis limit
    max_y = max(y)
    ylim = plt.ylim()[1]
    if max_y > ylim or max_y < 0.45*ylim:
        plt.ylim(0, int(max_y)+1)






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
        raise SystemExit("Error: Number of channels must be greater-equal than 1.")
    if n_channels % 2 != 1:
        raise SystemExit("Error: Number of channels must be an odd number.")
    if channel_weights is not None and len(channel_weights) != n_channels:
        raise SystemExit("Error: Provided channel weights does not match number of channels")
    if channel_weights is not None:
        for weight in channel_weights:
            if weight < 0:
                raise SystemExit("Error: Channel weights must be greater than 0.")
    if channel_weights is None:
        channel_weights = np.ones(n_channels)/n_channels
    elif np.sum(channel_weights) < 0.999999 or np.sum(channel_weights > 1.000001):
        print "Warning: Channel weights not normalised - normalising them..."
        channel_weights = np.asarray(channel_weights)/np.sum(channel_weights)

    #Create new artificial data array with extra zeros in the beginning and at the end to handle
    #the channels at the borders
    #extended_data = np.array(data)
    #extended_data = np.insert(extended_data, 0, np.zeros(n_channels//2))
    #extended_data = np.append(extended_data, np.zeros(n_channels//2))

    #Create new artificial data array with outer channels being mirrored and attached at the edges
    tempdata = np.array(data)
    extended_data = np.array(tempdata)
    extended_data = np.insert(extended_data, 0, np.flipud(tempdata)[-1*n_channels//2:])
    extended_data = np.append(extended_data, np.flipud(tempdata)[:n_channels//2])

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

def channel_weight_model(x, a):
    """Function to model the dependence of the absorbed light in a photo-diode and the channel
    number away from the center. Used to calculate the channel weights. Obtained from some crazy
    thoughts...

    Parameters
    ----------
    x: float, numpy array
        Point(s) where the evaluate the function.

    a: float
        Parameter which can be interpreted as the distance between the lightbar and the photodiodes

    Returns
    -------
    out: float, numpy array
        Evaluated points.
    """
    return np.absolute(a) / ( a**2 + x**2 )**2

def cos_weight_model(x):
    #Is zero at the edges of x
    return np.cos( np.pi/(2*x[-1]) * x )

def gaussian_weight_model(x):
    #Symmetric gaussian around zero where sigma is chosen to be one third of the outer edges
    #This results in the amplitude at the edges at 1 permille of the peak
    sigma = x[-1]/3
    return np.exp( -1/2 * (x/sigma)**2 )

def median_uniformity(data, n_parts=4):
    """Split data in n_parts, calc median for each split and return the ratio of the
    min(medians)/max(medians). A larger value translates to a better uniformity!"""
    medians = np.asarray(get_medians(data, n_parts))

    return min(medians)/max(medians)

def get_medians(data, n_parts=4):
    """Helper function for median uniformity."""
    datablocks = np.split(np.asarray(data), n_parts)
    medians = []
    for block in datablocks:
        medians.append(np.median(block))

    return medians


if __name__ == "__main__":
    atexit.register(exit_handler)

    #Reading the arguments
    parser = argparse.ArgumentParser(description='Monitoring lightbars with the Arduino board.')
    parser.add_argument('COMport', type=str, action="store",
                        help='The COM port to which the Arduino is connected.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='Turn on verbose output and behaviour.')

    options = parser.parse_args()
    verbose = options.verbose
    # Try to connect to the Arduino
    try:
        ser = serial.Serial(options.COMport, 115200, timeout=3)
        print "Successfully connected to Arduino on {}".format(ser.name)
    except OSError:
        raise ValueError("Arduino not found on {}".format(options.COMport))


    # Define the appearance of the plot
    fig = plt.figure(figsize=(16,8.9), facecolor = "white")
    permline, = plt.plot([], [], linewidth=2, color="r")    #Line that is triggered on click (for ref.)
    line, = plt.plot([], [], linewidth=2, color="b")
    median_lines = []
    for i in range(n_parts):
        median_lines.append( plt.plot([], [], linewidth=2, color="g")[0] )
    plt.plot([0,895], [3.63, 3.63], "k--")      #Saturation level
    plt.text(0.01, 3.65, "Saturation level", size=10)
    plt.ylabel("Intensity (Volts)", fontsize=18)
    plt.xlabel("Channel", fontsize=18)
    plt.xlim(0, 895)
    plt.xticks(range(0, 895, 100), fontsize=16)
    plt.ylim(0, 4)
    plt.yticks(fontsize=16)
    plt.grid()  #Plot grid


    # Boxes that show information about the mean and std across the different channels
    #LED brightness and integration time
    parameterbox = plt.text(0.006, 1.025, "no data", size=16, transform=plt.gca().transAxes,
                            bbox=dict(boxstyle="round", ec='k', fc='w', lw="1"), clip_on=False)

    #Draw boxes that contain the mean and std/mean
    box_x_blue = 0.81
    box_x_red = 0.55
    box_y = 1.02
    box_width = 0.18
    box_heigth = 0.092
    #Blue box
    plt.gca().add_patch( FancyBboxPatch((box_x_blue, box_y), box_width, box_heigth,
                                         transform=plt.gca().transAxes, clip_on=False,
                                         fc="none", ec="b", lw=2, boxstyle="round,pad=0.01") )
    blue_mean = plt.text(box_x_blue, box_y+0.071, "no data", size=16, transform=plt.gca().transAxes,
                         clip_on=False)
    blue_std = plt.text(box_x_blue, box_y+0.04, "", size=16, transform=plt.gca().transAxes,
                        clip_on=False)
    blue_uniformity = plt.text(box_x_blue, box_y+0.005, "", size=16, transform=plt.gca().transAxes,
                               clip_on=False)

    #Verbose elements
    if verbose:
        smearing_text = plt.text(0.34, 1.03, "Press keyboard button\nto smear data!",
                                transform=plt.gca().transAxes, clip_on=False, size=14)
        #Red box
        plt.gca().add_patch( FancyBboxPatch((box_x_red, box_y), box_width, box_heigth,
                                             transform=plt.gca().transAxes, clip_on=False,
                                             fc="none", ec="r", lw=2, boxstyle="round,pad=0.01") )
        red_mean = plt.text(box_x_red, box_y+0.071, "", size=16, transform=plt.gca().transAxes,
                             clip_on=False)
        red_std = plt.text(box_x_red, box_y+0.04, "", size=16,
                           transform=plt.gca().transAxes, clip_on=False)
        red_uniformity = plt.text(box_x_red, box_y+0.005, "Click to freeze\ncurrent data!", size=16,
                                   transform=plt.gca().transAxes, clip_on=False)
        #Indicate the inactive area
        plt.axvspan(0, n_remove_channels-0.5, color="r", alpha=0.6, label="Hidden area    ")
        plt.axvspan(895-n_remove_channels+0.5, 895, color="r", alpha=0.6)

    else:
        plt.title("Lightyield Measurement with Arduino\nand TAOS TSL2014")
        smearing_text = None
        red_mean = None
        red_std = None
        red_uniformity = None
        plt.xlim(n_remove_channels, 895-n_remove_channels)


    # Variables that store the parameters of LED brightness and integration time for the permanent
    # line
    blue_led = -1
    blue_int = -1
    red_led = -1
    red_int = -1



    #Markers to indicate the mean
    plt.plot(902, mean_green, "g_", ms=15, mew=2.5, clip_on=False)  #Limit for the mean (green area)
    plt.plot(902, mean_orange, "orange", marker="_", ms=15, mew=2.5, clip_on=False)  #Limit for the mean (green area)
    marker_blue, = plt.plot(-1000, 0.0, "b<", ms=10, clip_on=False)
    marker_red, = plt.plot(-1000, 0.0, "r<", ms=10, clip_on=False)
    plt.text(1.02, 0.5, "Mean values", size=20, transform=plt.gca().transAxes, rotation=270)


    #Button clicks
    if verbose:
        fig.canvas.mpl_connect('button_press_event', onClick)   #Mouse button click
        fig.canvas.mpl_connect('key_press_event', onPress)      #Key button press

    anim = animation.FuncAnimation(fig, update_line, fargs=[line, permline, blue_mean, blue_std,
                                   blue_uniformity, red_mean, red_std, red_uniformity, parameterbox,
                                   marker_blue, marker_red, smearing_text, median_lines],
                                   interval=200, blit=False, repeat=True, frames=None)
    plt.show()
