"""Extra lightweight procedural art backgrounds for RealityBlend.
No external media files are required; frames are generated with PIL.
"""
import math
from PIL import Image, ImageDraw

ART_BACKGROUNDS = [
    "Cyberpunk Alley", "Aurora Sky", "Retro Grid", "Candy Dream",
    "Volcanic Planet", "Cloud Kingdom", "Haunted Mansion",
    "Underwater City", "Comic Burst", "Golden Desert", "Moonlit Forest",
    "Tech Lab", "Rainy Window", "Sunrise Mountains", "Arcade Room"
]


def _base(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        p = y / max(1, h - 1)
        c = tuple(int(a + (b-a)*p) for a,b in zip(top,bottom))
        d.line((0,y,w,y), fill=c)
    return img.convert("RGBA")


def generate_art_background(name, size=(540,960), t=0.0):
    w,h=size
    palettes={
        "Cyberpunk Alley":((9,12,35),(52,8,58)), "Aurora Sky":((4,22,48),(18,74,72)),
        "Retro Grid":((24,8,50),(5,5,25)), "Candy Dream":((255,160,210),(100,150,255)),
        "Volcanic Planet":((25,7,5),(110,32,8)), "Cloud Kingdom":((95,165,235),(235,245,255)),
        "Haunted Mansion":((8,8,20),(48,22,54)), "Underwater City":((3,50,78),(2,10,38)),
        "Comic Burst":((255,214,65),(255,90,65)), "Golden Desert":((240,190,95),(115,55,35)),
        "Moonlit Forest":((8,20,28),(24,44,42)), "Tech Lab":((12,24,35),(30,62,76)),
        "Rainy Window":((28,35,48),(8,12,24)), "Sunrise Mountains":((255,170,100),(40,55,100)),
        "Arcade Room":((20,8,42),(6,18,38))}
    img=_base(size,*palettes.get(name,palettes[ART_BACKGROUNDS[0]]))
    d=ImageDraw.Draw(img)
    p=t*0.8
    if name=="Cyberpunk Alley":
        for i in range(10):
            x=i*w/9; hh=h*(.25+(i%4)*.07)
            d.polygon([(x-35,h),(x+45,h),(x+22,h-hh),(x-8,h-hh)],fill=(10,12,25,235))
            for y in range(int(h-hh+20),h-20,35): d.rectangle((x,y,x+10,y+7),fill=(255,70+(i%3)*50,180,170))
        for i in range(5):
            x=((i*.21+p*.04)%1)*w; d.line((x,h*.55,x+w*.12,h),fill=(40,220,255,90),width=5)
    elif name=="Aurora Sky":
        for i in range(7):
            pts=[]
            for x in range(-20,w+20,20): pts.append((x,h*(.18+i*.08)+math.sin(x/65+p+i)*35))
            d.line(pts,fill=(80,255,190,75),width=18)
        d.ellipse((w*.65,h*.12,w*.82,h*.29),fill=(220,245,255,150))
    elif name=="Retro Grid":
        horizon=h*.57
        for i in range(12):
            x=w/2+(i-6)*w*.18; d.line((w/2,h*.57,x,h),fill=(255,80,220,100),width=2)
        for j in range(9):
            y=horizon+(j/8)**1.8*h*.43; d.line((0,y,w,y),fill=(80,220,255,100),width=2)
        d.ellipse((w*.36,h*.15,w*.64,h*.43),outline=(255,100,220,100),width=5)
    elif name=="Candy Dream":
        for i in range(9):
            x=((i*.15+math.sin(p+i)*.03)%1)*w; y=h*(.15+(i%4)*.19)
            r=45+i%3*22; d.ellipse((x-r,y-r,x+r,y+r),fill=(255,255,255,35))
    elif name=="Volcanic Planet":
        d.ellipse((w*.55,-h*.1,w*1.25,h*.58),fill=(30,12,12,255),outline=(255,100,40,180),width=5)
        for i in range(12):
            x=((i*73+t*(20+i))%w); y=((i*97+t*(12+i%5))%h*.65)
            d.ellipse((x,y,x+3,y+8),fill=(255,130,35,190))
    elif name=="Cloud Kingdom":
        for i in range(10):
            x=((i*.13+p*.02)%1)*w; y=h*(.18+(i%5)*.12)
            for j in range(3): d.ellipse((x+j*35-45,y-25,x+j*35+55,y+35),fill=(255,255,255,145))
        d.polygon([(0,h*.75),(w*.25,h*.48),(w*.48,h*.73),(w*.7,h*.5),(w,h*.76),(w,h),(0,h)],fill=(100,120,150,130))
    elif name=="Haunted Mansion":
        d.rectangle((w*.25,h*.38,w*.75,h),fill=(12,10,18,245)); d.polygon([(w*.18,h*.4),(w*.82,h*.4),(w*.5,h*.18)],fill=(10,8,15,255))
        for x in (w*.34,w*.57): d.rectangle((x,h*.52,x+30,h*.66),fill=(255,210,85,120))
        for i in range(7):
            x=((i*91+t*7)%w); d.ellipse((x,h*.25+(i%3)*45,x+4,h*.27+(i%3)*45),fill=(180,180,210,110))
    elif name=="Underwater City":
        for i in range(12):
            x=i*w/11; hh=h*(.18+(i%5)*.09); d.rectangle((x,h-hh,x+28,h),fill=(5,20,38,190))
            d.rectangle((x+8,h-hh+20,x+15,h-hh+28),fill=(80,220,255,150))
        for i in range(15):
            x=(i*53+t*10)%w; y=(i*71+t*6)%h; d.ellipse((x,y,x+5,y+5),outline=(180,245,255,120),width=2)
    elif name=="Comic Burst":
        cx,cy=w*.5,h*.5
        for i in range(24):
            ang=i*math.pi*2/24; r=h
            d.line((cx,cy,cx+math.cos(ang)*r,cy+math.sin(ang)*r),fill=(255,255,255,90),width=5)
        d.ellipse((w*.28,h*.32,w*.72,h*.68),fill=(255,245,160,80),outline=(255,255,255,180),width=4)
    elif name=="Golden Desert":
        d.polygon([(0,h*.72),(w*.22,h*.55),(w*.45,h*.72),(w*.68,h*.52),(w,h*.7),(w,h),(0,h)],fill=(130,75,35,180))
        d.ellipse((w*.12,h*.12,w*.32,h*.32),fill=(255,230,145,150))
        for i in range(6):
            x=(i*.19+p*.02)%1*w; d.line((x,h*.78,x+20,h*.45),fill=(80,50,25,110),width=6)
    elif name=="Moonlit Forest":
        d.ellipse((w*.68,h*.08,w*.88,h*.28),fill=(235,240,210,170))
        for i in range(12):
            x=(i+.5)*w/12; hh=h*(.25+(i%4)*.08); d.polygon([(x,h),(x+35,h),(x+10,h-hh),(x-10,h-hh)],fill=(5,25,25,230))
    elif name=="Tech Lab":
        for i in range(7):
            y=h*(.15+i*.11); d.line((0,y,w,y),fill=(80,220,255,60),width=2)
        for i in range(8):
            x=(i+.5)*w/8; d.rectangle((x-28,h*.25,x+28,h*.55),outline=(100,220,255,100),width=3)
            d.ellipse((x-8,h*.34,x+8,h*.42),fill=(120,240,255,120))
    elif name=="Rainy Window":
        for i in range(70):
            x=(i*47+t*18)%w; y=(i*83+t*40)%h; d.line((x,y,x-7,y+22),fill=(180,210,230,100),width=2)
        d.rectangle((w*.1,h*.12,w*.9,h*.9),outline=(210,225,235,65),width=6)
    elif name=="Sunrise Mountains":
        d.ellipse((w*.35,h*.18,w*.65,h*.48),fill=(255,225,145,170))
        d.polygon([(0,h*.72),(w*.25,h*.42),(w*.42,h*.7),(w*.62,h*.36),(w,h*.73),(w,h),(0,h)],fill=(30,55,85,210))
        d.polygon([(0,h*.8),(w*.35,h*.58),(w*.55,h*.8),(w*.78,h*.55),(w,h*.82),(w,h),(0,h)],fill=(15,35,50,220))
    elif name=="Arcade Room":
        for i in range(6):
            x=w*(.08+i*.18); d.rounded_rectangle((x,h*.3,x+70,h*.8),radius=10,fill=(15,15,35,220),outline=(90,220,255,100),width=3)
            d.rectangle((x+12,h*.38,x+58,h*.55),fill=(120,40+(i%3)*50,220,120))
    return Image.alpha_composite(img,Image.new("RGBA",size,(0,0,0,0))).convert("RGB")


def preview_art_background(name,size=(270,480)):
    return generate_art_background(name,size,t=2.1)
