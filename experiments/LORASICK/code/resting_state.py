# created by Eduard Ort, 2019 

##########################
###  IMPORT LIBRARIES  ###
##########################
from psychopy import visual, core, event, monitors #import some libraries from PsychoPy

resp_key = 'q'
bg_color = 'black' 
fg_color='white'
size=0.4
screen_width=28
screen_distance=80
win_size= (1280,1024)

mon = monitors.Monitor('cocoLab',width = screen_width,distance = screen_distance)
mon.setSizePix(win_size)
win=visual.Window(size=win_size,color=bg_color,fullscr=1,units="deg",monitor=mon)
        
bigCircle = visual.Circle(win=win, size=size, pos=[0,0],lineColor=fg_color,fillColor=fg_color,autoLog=0)
rect_horiz = visual.Rect(win=win,width=size,height=size/6,fillColor=bg_color,lineColor=bg_color,autoLog=0)
rect_vert = visual.Rect(win=win,width=size/6,height=size,fillColor=bg_color,lineColor=bg_color,autoLog=0)
smallCircle = visual.Circle(win=win, size=size/6, pos=[0,0],lineColor=fg_color,fillColor=fg_color,autoLog=0)

fixPhase = [bigCircle,rect_horiz,rect_vert,smallCircle]

while resp_key not in event.getKeys():
    for i in fixPhase:
        i.draw()
    win.flip()

win.close()
core.quit()
