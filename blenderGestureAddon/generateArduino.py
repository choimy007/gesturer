#!/usr/bin/env python
# generateArduino.py
# Created by Skyler Williams
#
# Programatically generate C++ Arduino files using YAML configs options

# Import standard libraries
import os
import sys
import inspect

# Get the path to the current directory so we can add 3rd-party libraries
currentDirectory = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
# If we are using Python 3, grab libraries from the Blender addon
if sys.version_info >= (3, 0):
    addonLibs = currentDirectory + "/addon-gestureDeveloper/"
# Otherwise, we are using Python 2, so grab the Python 2 libraries
else:
    addonLibs = currentDirectory + "/python2Libs/"
# Make 3rd party libraries available for import
sys.path.append(addonLibs)
# Import 3rd party libraries
import yaml


def generateServoObjects(outputFile, offsetLine, numServos):
    servoObjectsString = ""
    for i in range(numServos):
        servoObjectsString += ("Servo myServo" + str(i) + ";\n")
        offsetLine += 1
    outputFile.write(servoObjectsString)


def generateServoPins(outputFile, offsetLine, numServos, servoPins):
    servoPinsString = ""
    for i in range (numServos):
        servoPinsString += ("int servoPin" + str(i) + " = " + str(servoPins[i]) + ";\n")
        offsetLine += 1
    outputFile.write(servoPinsString)


def generateAttachServos(outputFile, offsetLine, numServos):
    attachServosString = ""
    for i in range (numServos):
        attachServosString += ("  myServo" + str(i) + ".attach(servoPin" + str(i) + ");\n")
        offsetLine += 1
    outputFile.write(attachServosString)


def generateServoSwitch(outputFile, offsetLine, numServos):
    servoAttachString = ""
    servoAttachString += "    switch (currentServo) {\n"
    offsetLine += 1;
    for i in range (numServos):
        servoAttachString += ("      case " + str(i) + ":\n")
        servoAttachString += ("        myServo" + str(i) + ".write(data);\n")
        servoAttachString += ("        break;\n")
        offsetLine += 3
    servoAttachString += "    }\n"
    offsetLine += 1
    outputFile.write(servoAttachString)


def generateAddressingSwitch(outputFile, offsetLine, numServos):
    addressingSwitchString = ""
    addressingSwitchString += "    } else {\n"
    addressingSwitchString += "      switch (currentServo) {\n"
    offsetLine += 2
    for i in range (numServos):
        addressingSwitchString += ("    case " + str(i) + ":\n")
        addressingSwitchString += ("        myServo" + str(i) + ".write(data);\n")
        addressingSwitchString += ("        break;\n")
        offsetLine += 3
    addressingSwitchString += "      }\n"
    addressingSwitchString += "    }\n"
    offsetLine += 2
    outputFile.write(addressingSwitchString)


def generateCurrentServoIncrement(outputFile, offsetLine, numServos):
    currentServoIncrementString = ""
    currentServoIncrementString += ("    ++currentServo;\n")
    currentServoIncrementString += ("    if (currentServo == numServos) {\n")
    currentServoIncrementString += ("        currentServo = 0;\n")
    currentServoIncrementString += ("    }")
    offsetLine += 4
    outputFile.write(currentServoIncrementString)



def generateReceiveAddressByte(outputFile, offsetLine, numServos):
    receiveAddressByteString = ""
    receiveAddressByteString += ("      currentServo = data - 181;\n")
    receiveAddressByteString += ("      currentServo = (currentServo < 0) ? 0 : currentServo;\n")
    offsetLine += 2
    outputFile.write(receiveAddressByteString)


def main():

    # fileName = os.path.join(os.path.dirname(bpy.data.filepath), "../arduino/switching_motors_template/switching_motors_template.ino")
    switchingTemplate = open("motors_template.ino")

    yamlFileStream = open("gesturerConfigs.yaml").read()
    yamlConfigs = yaml.load(yamlFileStream, Loader=yaml.Loader)
    
    servoPins = yamlConfigs["servoPins"]
    numServos = yamlConfigs["numObjects"]
    motorIdentification = yamlConfigs["motorIdentification"]

    if (motorIdentification == "addressing"):
        outputFileName = "addressing_" + str(numServos) + "_motors.ino"
        insertionLines = yamlConfigs["addressingOffsets"]
    elif (motorIdentification == "switching"):
        outputFileName = "switching_" + str(numServos) + "_motors.ino"
        insertionLines = yamlConfigs["switchingOffsets"]
    else:
        outputFileName = "switching_" + str(numServos) + "_motors.ino"
        insertionLines = yamlConfigs["switchingOffsets"]

    templateLine = 0
    offsetLine = 0

    outputFile = open(outputFileName, "w")

    outputFile.write("// Generated by generateSwitchingTemplate.py with motors_template.ino as\n")
    outputFile.write("// base code, both written by Skyler Williams.\n")
    outputFile.write("// \n")
    outputFile.write("// Code for working with Blender Gesture Developer addon.\n")
    outputFile.write("// \n")

    replaceWithAddressingSwitch = False

    for line in switchingTemplate:        

        if templateLine in insertionLines:
            printObject = insertionLines[templateLine]

            if (printObject == "servoObjects"):
                generateServoObjects(outputFile, offsetLine, numServos)
            elif (printObject == "numServos"):
                outputFile.write("int numServos = " + str(numServos) + ";\n")
            elif (printObject == "servoPins"):
                generateServoPins(outputFile, offsetLine, numServos, servoPins)
            elif (printObject == "attachServos"):
                generateAttachServos(outputFile, offsetLine, numServos)
            elif (printObject == "servoSwitch"):
                generateServoSwitch(outputFile, offsetLine, numServos)
            elif (printObject == "currentServoIncrement"):
                generateCurrentServoIncrement(outputFile, offsetLine, numServos)
            elif (printObject == "receiveAddressByte"):
                generateReceiveAddressByte(outputFile, offsetLine, numServos)
            elif (printObject == "exceedsUpperBound"):
                outputFile.write("      data = 180;\n")
            elif (printObject == "addressingSwitch"):
                replaceWithAddressingSwitch = True
                generateAddressingSwitch(outputFile, offsetLine, numServos)

            if (replaceWithAddressingSwitch == False):
                outputFile.write(line)
            offsetLine += 1
            templateLine += 1
            replaceWithAddressingSwitch = False
        else:
            outputFile.write(line)
            offsetLine += 1
            templateLine += 1


if __name__ == '__main__':
    main()
