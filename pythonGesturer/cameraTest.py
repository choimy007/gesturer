import pygame
import pygame.camera 
from pygame.locals import *
import time

pygame.init()
pygame.camera.init()
cam = pygame.camera.Camera("/dev/video0", (640,480))
cam.start()

# wait for the camera to initialize
time.sleep(1.0)

# counter for naming files differently
i = 0
# initialize file name
fileName = ""

while(True):
	fileName = str(i)
	image = cam.get_image()
	pygame.image.save(image, fileName)
	i += 1
