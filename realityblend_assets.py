"""Built-in procedural assets for RealityBlend. No large media files required."""
import math
from PIL import Image, ImageDraw

BUILTIN_BACKGROUNDS = ["Neon City", "Sunset Gradient", "Ocean Motion", "Space Drift", "Studio Lights", "Green Park", "Abstract Shapes"]
STICK_FIGURE_STYLES = ["Classic", "Robot", "Ninja", "Professor"]


def _gradient(size, top, bottom, t):
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    drift = math.sin(t * 0.45) * 0.10
    for y in range(h):
        p = max(0.0, min(1.0, y / max(1, h - 1) + drift))
        c = tuple(int(a + (b - a) * p) for a, b in zip(top, bottom))
        d.line([(0, y), (w, y)], fill=c)
    return img


def generate_builtin_background(name, size=(540, 960), t=0.0):
    w, h = size
    name = name if name in BUILTIN_BACKGROUNDS else BUILTIN_BACKGROUNDS[0]
    palettes = {
        "Neon City": ((10, 18, 48), (100, 18, 85)),
        "Sunset Gradient": ((255, 110, 65), (45, 18, 72)),
        "Ocean Motion": ((18, 140, 180), (5, 28, 75)),
        "Space Drift": ((7, 10, 28), (48, 8, 72)),
        "Studio Lights": ((25, 25, 38), (78, 78, 100)),
        "Green Park": ((90, 180, 105), (18, 75, 48)),
        "Abstract Shapes": ((45, 18, 82), (8, 62, 88)),
    }
    img = _gradient(size, *palettes[name], t)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    phase = t * 0.7
    if name == "Neon City":
        horizon = int(h * .68)
        d.rectangle([0, horizon, w, h], fill=(7, 9, 20, 235))
        for i in range(12):
            x = int(i * w / 11); bh = int(h * (.10 + (i % 4) * .055))
            d.rectangle([x, horizon-bh, x+max(20,w//14), horizon], fill=(14,15,30,255))
            for wy in range(horizon-bh+18, horizon-8, 28):
                d.rectangle([x+7, wy, x+14, wy+8], fill=(255,210,85,185))
        for i in range(5):
            x = int(((i*.23)+phase*.035)%1.0*w)
            d.line([(x,horizon),(x+int(w*.16),h)], fill=(80,190,255,105), width=3)
    elif name == "Space Drift":
        for i in range(65):
            x=int((i*97+t*(10+i%6))%w); y=int((i*53+t*(5+i%4))%h); r=1+i%3
            d.ellipse([x-r,y-r,x+r,y+r], fill=(255,255,255,175))
        cx=int(w*(.72+.06*math.sin(t*.35))); cy=int(h*.28)
        d.ellipse([cx-75,cy-75,cx+75,cy+75], fill=(150,95,225,75))
        d.ellipse([cx-45,cy-45,cx+45,cy+45], fill=(225,185,255,85))
    elif name == "Ocean Motion":
        for j in range(8):
            y=int(h*(.48+j*.065))
            pts=[(x,y+int(9*math.sin(x/70+phase+j))) for x in range(0,w+20,20)]
            d.line(pts, fill=(140,235,250,90), width=5)
        d.ellipse([w*.12,h*.12,w*.88,h*.88], outline=(255,255,255,28), width=2)
    elif name == "Green Park":
        horizon=int(h*.64); d.rectangle([0,horizon,w,h], fill=(30,105,55,175))
        for i in range(9):
            x=int((i+.5)*w/9); y=horizon-20-(i%3)*18
            d.ellipse([x-55,y-70,x+55,y+25], fill=(20,90,45,155)); d.rectangle([x-5,y+5,x+5,horizon], fill=(80,55,35,170))
    elif name == "Studio Lights":
        for i in range(5):
            x=int(w*(.12+i*.19)+math.sin(phase+i)*35)
            d.ellipse([x-100,h*.08,x+100,h*.42], fill=(255,255,255,30))
        d.rectangle([w*.08,h*.72,w*.92,h*.74], fill=(255,255,255,28))
    else:
        for i in range(8):
            x=int(w*(.08+i*.13)+math.sin(phase+i)*55); y=int(h*(.16+(i%4)*.18)+math.cos(phase*.8+i)*35); r=65+(i%3)*28
            d.ellipse([x-r,y-r,x+r,y+r], fill=(255,255,255,24))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def preview_builtin_background(name, size=(360,640)):
    return generate_builtin_background(name, size, 1.7)


def generate_stick_figure(style="Classic", color=(35,35,45), size=(500,800)):
    """Create a transparent stick-figure sprite."""
    w,h=size; img=Image.new("RGBA",size,(0,0,0,0)); d=ImageDraw.Draw(img)
    style=style if style in STICK_FIGURE_STYLES else "Classic"; cx=w//2; r=int(w*.13); hy=int(h*.19); lw=max(7,int(w*.022))
    if style == "Robot":
        d.rounded_rectangle([cx-r,hy-r,cx+r,hy+r],radius=18,outline=color,width=lw,fill=(190,200,215,220))
        d.rectangle([cx-int(r*.62),hy-5,cx-int(r*.25),hy+5],fill=color); d.rectangle([cx+int(r*.25),hy-5,cx+int(r*.62),hy+5],fill=color)
    elif style == "Ninja":
        d.ellipse([cx-r,hy-r,cx+r,hy+r],fill=(30,30,38,240),outline=color,width=lw); d.rectangle([cx-r,hy-5,cx+r,hy+8],fill=(235,235,240,225))
        d.rectangle([cx-int(r*.55),hy-3,cx-int(r*.2),hy+3],fill=(15,15,20,255)); d.rectangle([cx+int(r*.2),hy-3,cx+int(r*.55),hy+3],fill=(15,15,20,255))
    elif style == "Professor":
        d.ellipse([cx-r,hy-r,cx+r,hy+r],fill=(235,205,170,225),outline=color,width=lw)
        d.ellipse([cx-int(r*.7),hy-int(r*.12),cx-int(r*.05),hy+int(r*.42)],outline=color,width=max(3,lw//2)); d.ellipse([cx+int(r*.05),hy-int(r*.12),cx+int(r*.7),hy+int(r*.42)],outline=color,width=max(3,lw//2))
    else:
        d.ellipse([cx-r,hy-r,cx+r,hy+r],fill=(245,205,175,225),outline=color,width=lw)
    neck=hy+r; shoulder=int(h*.35); hip=int(h*.62); hand=int(w*.28); leg=int(w*.20)
    d.line([(cx,neck),(cx,hip)],fill=color,width=lw); d.line([(cx,shoulder),(cx-hand,int(h*.50))],fill=color,width=lw); d.line([(cx,shoulder),(cx+hand,int(h*.50))],fill=color,width=lw)
    d.line([(cx,hip),(cx-leg,int(h*.90))],fill=color,width=lw); d.line([(cx,hip),(cx+leg,int(h*.90))],fill=color,width=lw)
    if style == "Robot": d.rounded_rectangle([cx-int(w*.12),shoulder,cx+int(w*.12),hip],radius=12,outline=color,width=lw)
    return img
