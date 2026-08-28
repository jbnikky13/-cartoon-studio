"""Shared lightweight motion presets for 2D characters."""
import math

MOTION_PRESETS = [
    "Idle", "Talk", "Walk", "Run", "Bounce", "Float", "Nod",
    "Wave", "Point", "Shake", "Spin", "Slide Left", "Slide Right", "Pulse"
]


def motion_values(motion, t, seed=0):
    """Return normalized dx, dy, rotation for a frame."""
    m=(motion or "Idle").lower()
    phase=t*2.0+seed
    dx=dy=rot=0.0
    if m=="idle":
        dy=math.sin(t*3.2+seed)*0.006; rot=math.sin(t*1.8+seed)*0.7
    elif m in ("talk","talking"):
        dy=math.sin(t*4.5+seed)*0.009; rot=math.sin(t*3.0+seed)*1.2
    elif m=="walk":
        dx=math.sin(t*2.8+seed)*0.035; dy=abs(math.sin(t*5.6+seed))*0.012; rot=math.sin(t*5.6+seed)*2.0
    elif m=="run":
        dx=math.sin(t*6.0+seed)*0.07; dy=abs(math.sin(t*12+seed))*0.025; rot=math.sin(t*12+seed)*4.0
    elif m=="bounce":
        dy=-abs(math.sin(t*4.5+seed))*0.035; rot=math.sin(t*4.5+seed)*1.5
    elif m=="float":
        dx=math.sin(t*1.5+seed)*0.018; dy=math.sin(t*2.0+seed)*0.03; rot=math.sin(t*1.4+seed)*2.0
    elif m=="nod":
        rot=math.sin(t*4.2+seed)*5.0; dy=math.sin(t*4.2+seed)*0.004
    elif m=="wave":
        dx=math.sin(t*4.8+seed)*0.014; dy=math.sin(t*4.8+seed)*0.008; rot=math.sin(t*4.8+seed)*3.0
    elif m=="point":
        dx=math.sin(t*1.5+seed)*0.006; rot=3.0+math.sin(t*2.0+seed)*0.8
    elif m=="shake":
        dx=math.sin(t*18+seed)*0.018; rot=math.sin(t*18+seed)*3.0
    elif m=="spin":
        rot=(t*80+seed*15)%360
    elif m=="slide left":
        dx=-0.08*math.sin(min(t,1.0)*math.pi/2)
    elif m=="slide right":
        dx=0.08*math.sin(min(t,1.0)*math.pi/2)
    elif m=="pulse":
        dy=-abs(math.sin(t*5+seed))*0.012
    return dx,dy,rot
