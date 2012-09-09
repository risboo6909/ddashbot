import pygame
import sys
import random
import time
import wx
import cv
import autopy

from pygame.locals import QUIT, KEYDOWN

# we need this image to recognize board position on the screen
upper_corner = cv.LoadImage("top.png", cv.CV_LOAD_IMAGE_GRAYSCALE)

# field width and height in cells
FIELD_WIDTH  = 10
FIELD_HEIGHT = 9

# width and height of each cell in px (debug only)
CELL_WIDTH   = 30
CELL_HEIGHT  = 30

NORMAL_MODE = 1
BOOST_MODE  = 1

mode = 0

board = [[0] * FIELD_WIDTH for _ in xrange(FIELD_HEIGHT)]

# initialize game window
pygame.init()

window = pygame.display.set_mode((600, 480))
screen = pygame.display.get_surface()

""" This function generates random board (used for debug) """
def generateBoard():
    for y in xrange(FIELD_HEIGHT):
        for x in xrange(FIELD_WIDTH):
            board[y][x] = COLORS[random.randint(0, len(COLORS) - 1)]
    return board

""" Analyze current board position and find the best move,
    algorithm complexity is O(n^2), where n is the linear size of the board 
"""
def findSolution(board):
    buf = [[0] * FIELD_WIDTH for _ in xrange(FIELD_HEIGHT)]
    buf[0][0] = 1
    flat = []
    
    # scan
    for y in xrange(FIELD_HEIGHT):

        for x in xrange(FIELD_WIDTH):
            if y > 0 and board[y][x] == board[y - 1][x]:
                buf[y][x] = buf[y - 1][x]
            elif x > 0 and board[y][x] == board[y][x - 1]:
                buf[y][x] = buf[y][x - 1]
            else:
                buf[y][x] = (y, x)

        for x in xrange(FIELD_WIDTH - 1, -1, -1):
            if x < FIELD_WIDTH - 1:
                if board[y][x] == board[y][x + 1]:
                    buf[y][x] = buf[y][x + 1]

        flat.extend(buf[y])
    
    results = {}
    counter = 0

    flat  = sorted(flat)
    prev_item = flat[0]

    for item in flat:
        if item == prev_item:
            counter += 1
        else:
            if counter not in results:
                results[counter] = [prev_item]
            else:
                results[counter].append(prev_item)
            prev_item = item
            counter = 1

    # for k in results.keys():
    #     print '%s:%s' % (k, results[k])

    return results

""" Screenshoter """
def grabScreen():   
    screen = wx.ScreenDC()
    size = screen.GetSize()
    bmp = wx.EmptyBitmap(size[0], size[1])
    mem = wx.MemoryDC(bmp)
    mem.Blit(0, 0, size[0], size[1], screen, 0, 0)
    del mem  # Release bitmap
    #bmp.SaveFile('screenshot.png', wx.BITMAP_TYPE_PNG)
    return wx.ImageFromBitmap(bmp)

""" Finds the position of a template inside an image using OpenCV """
def findMatch(img, template):
    result_cols = cv.GetSize(img)[0] - cv.GetSize(template)[0] + 1
    result_rows = cv.GetSize(img)[1] - cv.GetSize(template)[1] + 1
    result = cv.CreateImage((result_cols, result_rows), 32, 1)
    cv.MatchTemplate(img, template, result, cv.CV_TM_SQDIFF_NORMED)
    return cv.MinMaxLoc(result)

""" Find the play board position by locating the upper right corner of it """
def locateField(img, img_rgb, template, old_minLoc):
    global mode

    minVal, maxVal, minLoc, maxLoc = findMatch(img, template)
    mode = NORMAL_MODE

    if minVal > 0.1 and not old_minLoc:
        return None, None
    elif minVal > 0.1 and old_minLoc:
        minLoc = old_minLoc

    return extractBoard(img_rgb, minLoc)

""" Extract board image from screenshot """
def extractBoard(img_rgb, minLoc):
    # extract field image
    cv.SetImageROI(img_rgb, (minLoc[0] + 30, minLoc[1] + 25, 400, 360))
    
    # crop field from image
    pFieldImg = cv.CreateImage(cv.GetSize(img_rgb), img_rgb.depth, img_rgb.nChannels)
    cv.Copy(img_rgb, pFieldImg, None)

    return pFieldImg, minLoc

""" Recognize board raw image and build a matrix for further analysis """
def extarctGems(img):
    w, h = cv.GetSize(img)
    board = [[0] * FIELD_WIDTH for _ in xrange(FIELD_HEIGHT)]
    for y in xrange(20, h, 40):
        for x in xrange(20, w, 40):
            color = cv.Get2D(img, y, x)
            if color == (195.0, 213.0, 150.0, 0.0):
                # we've got diamond
                return False, (y, x)

            board[(y - 20) / 40][(x - 20) / 40] = color
            #cv.Set2D(img, y, x, (255, 255, 255))

    #cv.ShowImage("sample1", img)
    #cv.WaitKey()

    return True, board

def fromImage(filepath):
    img = cv.LoadImage(filepath, cv.CV_LOAD_IMAGE_COLOR)
    return img

def fromScreen():
    screenshot = grabScreen()
    cv_img = cv.CreateImageHeader((screenshot.GetWidth(), screenshot.GetHeight()), cv.IPL_DEPTH_8U, 3)
    cv.SetData(cv_img, screenshot.GetData())
    im_gray = cv.CreateImage(cv.GetSize(cv_img), cv.IPL_DEPTH_8U, 1)
    cv.CvtColor(cv_img, im_gray, cv.CV_RGB2GRAY);
    return cv_img, im_gray

app = wx.App()  # Need to create an App instance before doing anything

minLoc = []

# Main loop

while True:

    s = time.time()
    for event in pygame.event.get(): 
        if event.type == QUIT:  
            sys.exit(0)

    print 'taking screenshot'

    cv_img, im_gray = fromScreen()
    
    print 'analyzing'

    if not minLoc:
        field_img, minLoc = locateField(im_gray, cv_img, upper_corner, minLoc)
        print 'Game is not active!'
    else:
        field_img, _       = extractBoard(cv_img, minLoc)
        offset_x, offset_y = minLoc[0] + 30, minLoc[1] + 25
    
        result, board = extarctGems(field_img)

        if not result:
            # we've got a diamond
            autopy.mouse.move(offset_x + board[1], offset_y + board[0])
            autopy.mouse.toggle(True)
            autopy.mouse.toggle(False)
            print 'diamond!'
            time.sleep(1.7)
            continue    
        
        solved = findSolution(board)
        
        if solved and max(solved.keys()) >= 3:
            coord = solved[max(solved.keys())].pop()
            autopy.mouse.move(offset_x + 20 + coord[1] * 40, offset_y + 20 + coord[0] * 40)
            autopy.mouse.toggle(True)
            autopy.mouse.toggle(False)

            # this sleep timeouts are empirically tuned to keep a balance
            # between speed and accuracy (mb need more investigation of this)
            time.sleep(0.2)
            # if mode == NORMAL_MODE:
            #     time.sleep(0.1)
            # else:
            #     time.sleep(0)

    # uncomment this to see recognized board structure 
    # for y in xrange(FIELD_HEIGHT):
    #     for x in xrange(FIELD_WIDTH):
    #         pygame.draw.rect(screen, board[y][x], pygame.Rect(x * CELL_WIDTH, y * CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT), 0)
        
    # pygame.display.flip()

