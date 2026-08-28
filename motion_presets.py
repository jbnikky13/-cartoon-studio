"""Shared lightweight motion presets for Cartoon Studio and RealityBlend."""
import math

MOTION_PRESETS=["Idle","Talk","Walk","Run","Bounce","Float","Nod","Wave","Point","Shake","Spin","Slide Left","Slide Right","Pulse"]


def _one(m,t,seed=0):
    m=m.lower(); dx=dy=rot=0.0
    if m=="idle": dy=math.sin(t*3.2+seed)*.006; rot=math.sin(t*1.8+seed)*.7
    elif m in ("talk","talking"): dy=math.sin(t*4.5+seed)*.009; rot=math.sin(t*3+seed)*1.2
    elif m=="walk": dx=math.sin(t*2.8+seed)*.035; dy=abs(math.sin(t*5.6+seed))*.012; rot=math.sin(t*5.6+seed)*2
    elif m=="run": dx=math.sin(t*6+seed)*.07; dy=abs(math.sin(t*12+seed))*.025; rot=math.sin(t*12+seed)*4
    elif m=="bounce": dy=-abs(math.sin(t*4.5+seed))*.035; rot=math.sin(t*4.5+seed)*1.5
    elif m=="float": dx=math.sin(t*1.5+seed)*.018; dy=math.sin(t*2+seed)*.03; rot=math.sin(t*1.4+seed)*2
    elif m=="nod": rot=math.sin(t*4.2+seed)*5; dy=math.sin(t*4.2+seed)*.004
    elif m=="wave": dx=math.sin(t*4.8+seed)*.014; dy=math.sin(t*4.8+seed)*.008; rot=math.sin(t*4.8+seed)*3
    elif m=="point": dx=math.sin(t*1.5+seed)*.006; rot=3+math.sin(t*2+seed)*.8
    elif m=="shake": dx=math.sin(t*18+seed)*.018; rot=math.sin(t*18+seed)*3
    elif m=="spin": rot=(t*80+seed*15)%360
    elif m=="slide left": dx=-.08*math.sin(min(t,1)*math.pi/2)
    elif m=="slide right": dx=.08*math.sin(min(t,1)*math.pi/2)
    elif m=="pulse": dy=-abs(math.sin(t*5+seed))*.012
    return dx,dy,rot


def motion_values(motion,t,seed=0):
    """Return normalized dx,dy,rotation. Supports combinations like Talk+Walk."""
    parts=[p.strip() for p in str(motion or "Idle").split("+") if p.strip()]
    if not parts: parts=["Idle"]
    vals=[_one(p,t,seed+i*.37) for i,p in enumerate(parts)]
    return tuple(sum(v[j] for v in vals) for j in range(3))
