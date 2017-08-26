# pythonGesturer.py
# Created by Skyler Williams
#
# Python script for communicating gestural animation data to an Arduino from
# CSV files.
# 
#!/usr/bin/python
import csv
import pygame
import serial
import struct
import sys
import time
import yaml
import random
import numpy as np
from random import randint

# Import needed for camera ######################################################
# make sure to install pygame in order for the import to work
import pygame
import pygame.camera 
from pygame.locals import *
#################################################################################

import copy


###################### Implementation Specific Definitions #####################
frameCounter = 0

################################################################################

# Global Variables

# Array to store previous servo angles, so we know when to send new values to
# the servos
previousServoAngles = []

# Value to represent the new gesture to be performed, when this value is 
# changed in updateGesture() the program smooths between the current gesture
# and this new gesture
newGesture = 0

# Create a global timeout variable, so we can reset the timeout after performing
# a non-blocking read
globalTimeout = None

# Create a PySerial port with infinite timeout (blocks on reads), but not yet
# connected to a hardware port (read in from configs)
serialPort = serial.Serial(None, 9600, timeout = globalTimeout)

# The user will input the total number of gestures
totalGestures = 0

# a variable to keep track of the current branch
currentBranch = 0

# a variable to keep track of the new branch
newBranch = 0

# a boolean for checking whether in transition gesture
transitionBool = False

# a variable for storing in the next gesture when transition occurs 
nextGesture = 0

# a variable to store file name for pictures taken by the camera
imageName = ""

###################### Implementation Specific Functions #######################

"""
A 2d array of gestures, divided into groups by which branch they are on
Each array represents a branch. If there is only one branch, put all 
gestures in one array.
Ex) [[0,1,2]]
If on multiple branches:
Ex) [[0],[2],[4]]
Make sure to not include the transition gesture as part of branch gesture
"""
gestureGroupList = [[0,1,2]]
npGesture = np.array(gestureGroupList)

"""
List of transition gestures
Ex) [1,3,5]
"""
transitionList = []

""" 
A list of transition gestures, marked [x,y,z] where 
x is the starting branch, 
y is the finish branch, and 
z is the gesture number
Ex) [[0,1,1],[1,2,3],[2,0,5]]
"""
transitionGestures = []

# list of nontransition gestures - automatically generated
l1 = npGesture.flatten()
l3 = [x for x in list(l1) if x not in transitionList]

# Simple example of changing the newGesture to a constant value
def updateGesture(frame, csvGestureData, csvGestureLength):
    global newGesture
    global frameCounter
    global gestureGroupList
    global transitionGestures
    global newBranch
    global transitionBool
    global l3
    global currentBranch

    chosen = False

    # how many frames before a new gesture must be put in
    changeGestureFrame = 10

    # how many gestures there are
    totalGestures = 6

    # Choose between user input random gestures
    if frame == changeGestureFrame and transitionBool == False:
        newGesture = random.choice(l3)
        print ("Current branch is: " + str(currentBranch))
        # see which branch the new gesture belongs to and update accordingly
        counter = 0
        for sub_list in gestureGroupList:
            for j in sub_list:
                if j == newGesture:
                    newBranch = counter
                    print ("Future branch is: " + str(newBranch))
            counter += 1


################################################################################


def gestureSmooth(sleepTime, numObjects, startPosArray, endPosArray):
    print("Smoothing between gestures...")

    # Right now position arrays start as strings, so convert them to integers
    startPosArray = map(int, startPosArray)
    endPosArray = map(int, endPosArray)

    # Find the maximum distance between positions for the start and end positions
    # of each object
    maxDelta = 0
    for i in range(numObjects):
        testDelta = abs(startPosArray[i + 1] - endPosArray[i + 1])
        if maxDelta < testDelta:
            maxDelta = testDelta

    # Setup temporary buffer for transitionary positions
    servoValues = [0] * numObjects
    # Initialize the temporary buffer with the starting positions
    for i in range(numObjects):
        servoValues[i] = startPosArray[i + 1]

    startTime = time.time()
    endTime = time.time()

    # Linear smoothing over the range of the longest distance
    for i in range(maxDelta):
        startTime = time.time()

        # For each object
        for i in range(numObjects):
            # Linearly increment/decrement the servo value towards the end 
            # position value, how/if appropriate
            if servoValues[i] > endPosArray[i + 1]:
                servoValues[i] -= 1
            elif servoValues[i] < endPosArray[i + 1]:
                servoValues[i] += 1
            # Otherwise, the servo value is the end position value, and that 
            # servo stops animating

            # print("Servo value is: " + str(servoValues[i]))
            # Write out the servo value to the Arduino and read back the return
            serialPort.write(struct.pack('B', servoValues[i]))
            serialRead = serialPort.read()

        endTime = time.time()
        timeDifference = endTime - startTime

        # If rendering the frame on the robot took less time than the sleep
        # time, subtract the timeDifference from the sleepTime and sleep 
        # that amount to create the proper frame rate
        if 0 < timeDifference and timeDifference < sleepTime:
            time.sleep(sleepTime - timeDifference)
        else:
            print("Execution time exceeded the frame rate...")
        # Otherwise, we do not want to sleep as we have already spent more
        # time than the frame rate   


def frame_handler(scene, numObjects, csvFile, motorIdentification):
    # Create an array to store the angles we get from the Blender scene, and a
    # bool to see if we should send these values to the Arduino
    newAngles = [0] * numObjects
    shouldResend = False

    # We will be modifying this global variable, so we declare it global
    global previousServoAngles

    # main function will use the name to store the picture
    global imageName

    # Generalized loop for putting an arbitrary number of object parameters out 
    # on the serial connection
    for i in range(numObjects):
        # We index plus 1 into the csvFile since there is timestep data
        servoAngle = int(csvFile[scene][i + 1])
        if (servoAngle > 180):
            servoAngle = 180
        elif (servoAngle < 0):
            servoAngle = 0
        newAngles[i] = servoAngle
        # print("Servo " + str(i) + "is: " + str(servoAngle))

        # If the angle of a motor has changed, rewrite them all to Arduino
        if servoAngle != previousServoAngles[i]:
            shouldResend = True

            previousServoAngles[i] = newAngles[i]

        # Variable needed for camera ###############################################
        # generate the file name for the picture
        imageName = '_'.join(map(str,newAngles))
        ############################################################################

    # If we should resend the motor positons, loop through and send each based
    # on the motor identification scheme (addressing/switching)
    if shouldResend == True:
        for i in range(numObjects):
            # If we are addressing motors, first send "i"
            if motorIdentification == "addressing":
                serialPort.write(struct.pack('B', (181 + i)))
                serialRead = serialPort.read()
                # Make sure the value read by Arduino and returned is the same as 
                # that we sent, otherwise exit the program
                if ord(serialRead) != (181 + i):
                    sys.exit()
                    print("Serial send not equal to serial return")
                    break

            serialPort.write(struct.pack('B', newAngles[i]))
            # previousServoAngles[i] = newAngles[i]
            # print("Write angle " + str(i) + " is: " + str(newAngles[i]))

            serialRead = serialPort.read()
            # Make sure the value read by Arduino and returned is the same as 
            # that we sent, otherwise exit the program
            if ord(serialRead) != newAngles[i]:
                sys.exit()
                print("Serial send not equal to serial return")
                break
        shouldResend = False


def main():
    # We will be modifying this global variable, so we declare it global
    global previousServoAngles
    global newGesture
    global currentBranch
    global newBranch
    global transitionBool
    global nextGesture
    global gestureGroupList
    global backwards

    # initialize the camera ###################################################################
    global imageName
    pygame.init()
    pygame.camera.init()
    cam = pygame.camera.Camera("/dev/video0", (640,480))
    cam.start()
    ###########################################################################################

    # Read in the YAML configs
    fileName = "gesturerConfigs.yaml"
    fileStream = open(fileName).read()

    switchNum = 400
    currentGesture = 0
    # find which branch currentGesture is in
    counter = 0
    for sub_list in gestureGroupList:
        for j in sub_list:
            if j == newGesture:
                currentBranch = counter
        counter += 1
    switchCount = 0

    configs = yaml.load(fileStream, Loader=yaml.Loader)
    # Load the YAML configs into global variables for easy access
    numObjects = configs["numObjects"]
    numGestures = configs["numGestures"]
    motorIdentification = configs["motorIdentification"]
    previousServoAngles = [0] * numObjects

    serialPort.port = configs["serialPort"]

    # TODO: Read in a single CSV file (name in the YAML). DONE
    # TODO: Calculate indexing into the CSV for each individual gesture, make
    # a dictionary/array to know how to index into the gestures
    # OR just read each gesture into a separate file! DONE (into separate arrays).

    csvOutputName = configs["csvOutputName"]

    # Read in the gesture csv files
    csvInputFile = open(csvOutputName, 'rt')
    reader = csv.reader(csvInputFile)
    row_count = 0
    # Will be a list of gesture number lists, each containing a list of the 
    # positions for each motor at each frame of the gesture
    csvGestureData = []
    for gesture in range(numGestures):
        # Append a new list for each gesture, if we multiply an empty list it is
        # three references to the same list!
        csvGestureData.append([])
    csvGestureLength = [0] * numGestures

    # TODO: For each gesture, create a new entry in csvGestureData and populate
    # it with csv values (by appending). DONE
    gestureCount = 0
    # Read through the CSV file and populate the gesture data/length arrays 
    for row in reader:
        # If the first item in the CSV row is a "*", we have reached the end of
        # a gesture
        if row[0] == "*":
            csvGestureLength[gestureCount] = len(csvGestureData[gestureCount])
            gestureCount += 1
        # Otherwise, continue adding to the current gesture
        else:
            csvGestureData[gestureCount].append(row)

    # In case there was no "*" at the end of the last gesture, we set the last 
    # gesture length
    if gestureCount == (numGestures - 1):
        csvGestureLength[gestureCount] = len(csvGestureData[gestureCount])

    # Close the CSV input file
    csvInputFile.close()

    # TODO: Append the Backward gestures in reverse order to the back of gestures
    # So that first transition gesture backwards can be called with -1
    for i in transitionList[::-1]:
        # get the transition gesture to be reversed
        tempGesture = copy.deepcopy(csvGestureData[i])
        # reverse the transition gesture
        tempGesture.reverse()
        for i in range(len(csvGestureData)):
            tempGesture[i][0] = str(i)
        # append the transition gesture to the end of the gesture data
        csvGestureData.append(tempGesture)
        # update csvGestureLength
        csvGestureLength.append(len(csvGestureData[-1]))

    # Start the number of frames as the length of the currentGesture
    numFrames = csvGestureLength[currentGesture]

    serialPort.open()
    # Connecting time for Arduino
    time.sleep(3)

    # Set frame rate and corresponding sleep rate
    # TODO: import these from the YAML configs and have them be set by the user
    # to correspond with how the gesture was generated (in Blender or otherwise)
    frameRate = 24
    sleepTime = 1./frameRate
    # absoluteSleepTime = 1./frameRate

    # Main loop for executing gestures/the logic for switching between them
    # TODO: Add modular logic for switching between gestures. MOSTLY DONE (just 
    # need to write an example updateGesture())

    startTime = time.time()
    endTime = time.time()

    # Variable for Camera #######################################################################
    # counter for recording images
    counter = 0
    #############################################################################################

    while True:
        for currentFrame in range(numFrames):
            startTime = time.time()
            
            frame_handler(currentFrame, numObjects, csvGestureData[currentGesture],  motorIdentification)
            # Save image from Camera ####################################################################
            # save the image
            imageName = str(counter) + "_" + imageName
            image = cam.get_image()
            pygame.image.save(image, imageName)
            counter += 1
            #############################################################################################

            # Sleep to create a frame rate
            # endTime = time.time()
            # timeDifference = endTime - startTime
            # print(endTime - startTime)
            # if timeDifference < absoluteSleepTime:
            #     sleepTime = absoluteSleepTime - timeDifference
            # else:
            #     sleepTime = absoluteSleepTime
            # print(sleepTime)

            # LOGIC FOR SWITCHING "currentGesture" GOES HERE
            # it will not do anything if the gesture is a transition gesture
            if not transitionBool:
                updateGesture(currentFrame, csvGestureData, csvGestureLength)


            # if the new gestures is not the current gesture,
            if currentGesture != newGesture:
                print("Switching Gestures...")
                print("currentGesture is: " + str(currentGesture))


            ############ TRANSITION ###################################################
                # check if the two gestures are of different branches
                if currentBranch != newBranch:
                    print "Different Branches"
                    # if they are not on the same branch, do a transition gesture, if it exists
                    # first check if there is a transition gesture
                    for sub_list in transitionGestures:
                        # if transition gesture exists, set the transitionBool as True
                        # the transitionBool will guarantee that the gesture will not change with updateGesture
                        # and store the newGesture to use in the future
                        # and set the new gesture as transition gesture
                        if sub_list[0] == currentBranch and sub_list[1] == newBranch: 
                            transitionBool = True
                            nextGesture = newGesture
                            newGesture = sub_list[2]
                        # if the transition gesture is present but we need to play it backwards
                        elif sub_list[0] == newBranch and sub_list[1] == currentBranch:
                            transitionBool = True
                            nextGesture = newGesture
                            # get the index of the newGesture
                            backGesture = sub_list[2]
                            # find which transition gesture it is
                            backGesture = transitionList.index(backGesture)
                            # add 1 and negate it for correct position of the transition
                            newGesture = -(backGesture+1)
                    # change the current branch to new branch
                    currentBranch = newBranch
                    print("Playing transition gesture...")

            ############ TRANSITION ###################################################

                startPosArray = [0] * numObjects
                endPosArray = [0] * numObjects
                oldGesture = currentGesture
                currentGesture = newGesture

                print("currentGesture is: " + str(currentGesture))

                startPosArray = csvGestureData[oldGesture][currentFrame]
                endPosArray = csvGestureData[currentGesture][0]
                numFrames = csvGestureLength[currentGesture]

                # Note, if you want linear smoothing between gestures, create arrays 
                # containing the start and end positions of each object and uncomment
                # the following line
                gestureSmooth(sleepTime/2, numObjects, startPosArray, endPosArray)

                # BE SURE TO "break" AT THE END OF THE SWITCHING GESTURES LOGIC
                break   

            if transitionBool == True and (currentFrame+1) == numFrames:
                print "transition finished"
                transitionBool = False
                startPosArray = [0] * numObjects
                endPosArray = [0] * numObjects
                oldGesture = currentGesture
                currentGesture = nextGesture
                newGesture = currentGesture

                print("currentGesture is: " + str(currentGesture))

                startPosArray = csvGestureData[oldGesture][currentFrame]
                endPosArray = csvGestureData[currentGesture][0]
                numFrames = csvGestureLength[currentGesture]

                # Note, if you want linear smoothing between gestures, create arrays 
                # containing the start and end positions of each object and uncomment
                # the following line
                gestureSmooth(sleepTime/2, numObjects, startPosArray, endPosArray)

            endTime = time.time()

            timeDifference = endTime - startTime
            # print(timeDifference)

            # If rendering the frame on the robot took less time than the sleep
            # time, subtract the timeDifference from the sleepTime and sleep 
            # that amount to create the proper frame rate
            if 0 < timeDifference and timeDifference < sleepTime:
                time.sleep(sleepTime - timeDifference)
            else:
                print("Execution time exceeded the frame rate...")

            #time.sleep(0.4)

            # Otherwise, we do not want to sleep as we have already spent more
            # time than the frame rate

            # startTime = time.time()

'''
Code used for Tkinter GUI
##################### Python Tkinter GUI #######################################
#import Tkinter as tk
#import threading
#from Tkinter import *
class GesturerGUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        # set number of total gestures
        self.v = tk.StringVar()
        self.v.set("0")
        self.entry = tk.Entry(self, textvariable=self.v)
        self.button = tk.Button(self, text="Set Total number of Gestures", command=self.on_button)
        self.entry.pack()
        self.button.pack()

        # set frame change rate
        self.v2 = tk.StringVar()
        self.v2.set("0")
        self.entry2 = tk.Entry(self, textvariable=self.v2)
        self.button2 = tk.Button(self, text="Set Frame Change Rate", command=self.set_frame_rate)
        self.entry2.pack()
        self.button2.pack()

        # allow user to manually change gesture
        self.v3 = tk.StringVar()
        self.v3.set("0")
        self.entry3 = tk.Entry(self, textvariable=self.v3)
        self.button3 = tk.Button(self, text="Manually Change Gesture Number", command=self.changeGesture)
        self.entry3.pack()
        self.button3.pack()

        # allow user to manually change gesture
        # put in array for transition gesture numbers
        self.v4 = tk.StringVar()
        self.v4.set("0")
        self.entry4 = tk.Entry(self, textvariable=self.v4)
        self.button4 = tk.Button(self, text="Enter Transition Gesture Number", command=self.transition)
        self.entry4.pack()
        self.button4.pack()

        # put in array for groups of gestures
        # if next gesture is in a gesture group that needs transition gesture,
        # main will play transition before playing other gestures
        # make sure to match gesture groups to transition gestures:
        # i.e.: transition gesture 1 for transitioning to gesture group 1
        # Input must be integers separated by commas
        self.v5 = tk.StringVar()
        self.v5.set("0")
        self.entry5 = tk.Entry(self, textvariable=self.v5)
        self.button5 = tk.Button(self, text="Enter Gesture Group", command=self.group)
        self.entry5.pack()
        self.button5.pack()

        self.v6 = tk.StringVar()
        self.v6.set("0")
        self.entry6 = tk.Entry(self, textvariable=self.v6)
        self.button6 = tk.Button(self, text="Enter Gesture Group of 1st Gesture", command=self.beginGroup)
        self.entry6.pack()
        self.button6.pack()

        # button to play the gestures
        self.button = tk.Button(self, text = "Play Gestures", command = self.startGestures)
        self.button.pack()

    def on_button(self):
        global totalGestures
        totalGestures = self.v.get()
        print('There is a total of ' + self.v.get() + ' gestures.')

    def set_frame_rate(self):
        global changeGestureFrame
        changeGestureFrame = self.v2.get()
        print('Script will randomize gestures every ' + self.v2.get() + ' frames.')

    def startGestures(self):
        threads = []
        t = threading.Thread(target=main)
        threads.append(t)
        self.button.config(state=tk.DISABLED)
        print 'starting main thread'
        t.start()

    def changeGesture(self):
        global newGesture
        newGesture = int(self.v3.get())
        print('The new gesture is: ' + self.v3.get())

    def transition(self):
        global transitionGestures
        s = int(self.v4.get())
        transitionGestures.append(s)
        print(transitionGestures)

    def group(self):
        global gestureGroups
        s = self.v5.get()
        gestureGroups.append(s)
        print(gestureGroups)

    def beginGroup(self):
        global currentGesture
        currentGesture = int(self.v6.get())

app = GesturerGUI()
app.mainloop()
##################### Python Tkinter GUI #######################################

#b = Button(text="click me", command=main)
#b.pack()

#mainloop()
>>>>>>> parent of f5ac6fc... Random gestures on 3 motors now work. A simple GUI is in place, allowing the user to put total number of gestures and frame change rate without going into the code. IMPORTANT: to rerun with different parameters, make sure to shut off the GUI and ctrl+c in the terminal so that nothing is running.

#b = Button(text="click me", command=main)
#b.pack()

#mainloop()
>>>>>>> parent of f5ac6fc... Random gestures on 3 motors now work. A simple GUI is in place, allowing the user to put total number of gestures and frame change rate without going into the code. IMPORTANT: to rerun with different parameters, make sure to shut off the GUI and ctrl+c in the terminal so that nothing is running.

################################################################################            
'''

if __name__ == "__main__":  
    main()  
