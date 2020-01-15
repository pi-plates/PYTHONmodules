import contextlib
with contextlib.redirect_stdout(None):
    import pygame
pygame.init()

MAXWIDTH=1000
MAXHEIGHT=100
MAXLINES=12
FONTSIZE=128
COLOR = (0,128,0)
units=['units']*MAXLINES
val=[0.0]*MAXLINES
desc=['']*MAXLINES
lines=1
size = width, height = MAXWIDTH, MAXHEIGHT
meterOpen=False

def openMETER(linesel=None):
    global font, screen, size, height, width, lines, units, val, meterOpen
    if linesel is None:
        size = width, height = MAXWIDTH, MAXHEIGHT
        lines=1
    else:    
        assert ((linesel>=1) and (linesel<=MAXLINES)), "Line count must be between 1 and "+str(MAXLINES)
        size = width, height = MAXWIDTH, MAXHEIGHT*linesel
        lines=linesel
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption('TINKERplate Meter')
    font=pygame.font.SysFont(None,FONTSIZE)  
    refresh()
    meterOpen=True
    
def closeMETER():
    global meterOpen
    if(meterOpen):
        pygame.display.quit()
        meterOpen=False
         
def setMETER(value,unit,descriptor,linesel=None):
    global size, height, width, lines, units, val, desc
    assert(meterOpen), "You must open a meter before you write to it."
    if linesel is None:
        line=1
    else: 
        assert (linesel<=lines),"That line does not exist. Close your current meter and reopen with the correct number of lines."
        assert ((linesel>=1) and (linesel<=MAXLINES)), "Line count must be between 1 and "+str(MAXLINES)
        line=linesel  
    desc[line-1]=descriptor
    val[line-1]=value
    units[line-1]=unit
    refresh()

def setTITLE(title):
    pygame.display.set_caption(title)
    
def setCOLOR(newcolor):
    global COLOR
    assert (len(newcolor)==3), "Only three arguments accepted for color."
    assert (newcolor[0]>=0 and newcolor[0]<=255), "Argument must be between 0 and 255"
    assert (newcolor[1]>=0 and newcolor[1]<=255), "Argument must be between 0 and 255"
    assert (newcolor[2]>=0 and newcolor[2]<=255), "Argument must be between 0 and 255"    
    COLOR=newcolor
    
def refresh():
    global acreen, size, height, width, lines, units, val, desc
    screen.fill((0,0,0))
    for i in range(lines):
        text_surface = font.render(desc[i]+str("%7.3f"%(val[i]))+' '+units[i], True, COLOR)
        text_rect = text_surface.get_rect(center=(width/2, height*(2*i+1)/(2*lines)))       
        screen.blit(text_surface,text_rect)
    for i in range(lines):        
        pygame.draw.line(screen,COLOR,[0,(i+1)*height/lines],[width,(i+1)*height/lines],3)           
    pygame.display.update()