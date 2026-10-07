#!/usr/bin/env python3
"""Render deterministic social graphics from data/report.json."""
from pathlib import Path
import base64
import io
import json
import urllib.request
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "visuals"
W, H = 1600, 1000
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ASSETS = ROOT / "visual_assets"


def font(size, bold=False): return ImageFont.truetype(BOLD if bold else FONT, size)
def text(d, xy, value, size, fill="white", bold=False, anchor=None):
    d.text(xy, str(value), font=font(size, bold), fill=fill, anchor=anchor)
def fit(value, n):
    value = str(value)
    return value if len(value) <= n else value[:n - 1] + "…"
def rect(d, box, fill, outline=None, width=2, radius=18):
    d.rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)
def base(title, subtitle, accent="#f4c542", bg="#071421"):
    im = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line((0, y, W, y), fill=tuple(int(int(bg[i:i+2],16)*(1-t*.45)) for i in (1,3,5)))
    for x in range(0, W, 100): d.line((x, 0, x-340, H), fill="#10263a", width=2)
    d.rectangle((0, 0, W, 16), fill=accent)
    text(d, (W//2, 72), title.upper(), 76, "white", True, "mm")
    text(d, (W//2, 132), subtitle.upper(), 24, accent, True, "mm")
    d.line((110, 165, W-110, 165), fill=accent, width=4)
    return im, d
def footer(d, report):
    text(d, (W//2, H-26), f"THROUGH WEEK {report['through_week']}  •  TRANSACTIONS SINCE AUGUST 23, 2026  •  AUTO-GENERATED", 20, "#aab8c5", True, "mm")
def player_name(report, pid):
    p = report['players'].get(str(pid), {})
    return p.get('full_name') or p.get('first_name','')+' '+p.get('last_name','') or str(pid)

def art(name):
    path = ASSETS / name
    if path.exists(): return Image.open(path).convert('RGB')
    encoded = ASSETS / (name + '.b64')
    return Image.open(io.BytesIO(base64.b64decode(encoded.read_text()))).convert('RGB')

@lru_cache(maxsize=256)
def headshot(pid, size=72):
    try:
        with urllib.request.urlopen(f"https://sleepercdn.com/content/nfl/players/{pid}.jpg", timeout=1.5) as response:
            im = Image.open(io.BytesIO(response.read())).convert('RGB')
        im.thumbnail((size, size), Image.Resampling.LANCZOS)
        tile = Image.new('RGB', (size, size), '#172434')
        tile.paste(im, ((size-im.width)//2, size-im.height))
        return tile
    except Exception:
        return Image.new('RGB', (size, size), '#25384b')

def paste_circle(canvas, source, xy, size, border='#ffffff'):
    source = source.resize((size,size), Image.Resampling.LANCZOS)
    mask = Image.new('L',(size,size)); ImageDraw.Draw(mask).ellipse((0,0,size-1,size-1),fill=255)
    ring = Image.new('RGB',(size+8,size+8),border); ring_mask=Image.new('L',(size+8,size+8)); ImageDraw.Draw(ring_mask).ellipse((0,0,size+7,size+7),fill=255)
    canvas.paste(ring,(xy[0]-4,xy[1]-4),ring_mask); canvas.paste(source,xy,mask)

def player_line(canvas, d, report, player, x, y, width, color):
    paste_circle(canvas, headshot(player['player_id'],64),(x,y),64,color)
    text(d,(x+78,y+12),fit(player_name(report,player['player_id']),14),16,'white',True)
    text(d,(x+78,y+40),f"{player['points']:.2f} PTS",24,color,True)

def rich_person_tracker(report, key, header_name, ryan=False):
    rid=report['trackers'][key]; trades=[]
    for trade in report['trades']:
        side=next((s for s in trade['sides'] if s.get('roster_id')==rid),None)
        if side: trades.append((trade,side))
    rows=max(1,(len(trades)+2)//3); height=354+rows*520+(300 if ryan else 230)
    canvas=Image.new('RGB',(W,height),'#070c12'); canvas.paste(art(header_name).resize((W,354)),(0,0)); d=ImageDraw.Draw(canvas)
    total_in=total_out=0
    for i,(trade,side) in enumerate(trades):
        row,col=divmod(i,3); cw=500; x=28+col*524; y=370+row*520
        rect(d,(x,y,x+cw,y+490),'#111820','#d6b34a' if not ryan else '#d9e4ec',3,16)
        text(d,(x+cw//2,y+28),f"TRADE {i+1}  •  SCORING FROM WEEK {trade['first_scoring_week']}",20,'white',True,'mm')
        mid=x+cw//2; d.rectangle((x+10,y+55,mid-4,y+375),fill='#3a1017'); d.rectangle((mid+4,y+55,x+cw-10,y+375),fill='#073725')
        text(d,(x+cw*.25,y+82),'GAVE AWAY',18,'#ff6b75',True,'mm'); text(d,(x+cw*.75,y+82),'RECEIVED',18,'#65f69a',True,'mm')
        for j,p in enumerate(side.get('sent_players',[])[:3]): player_line(canvas,d,report,p,x+18,y+112+j*82,220,'#ff7b83')
        for j,p in enumerate(side.get('received_players',[])[:3]): player_line(canvas,d,report,p,mid+12,y+112+j*82,220,'#68f39b')
        total_in+=side['received_points']; total_out+=side['sent_points']
        text(d,(x+cw*.25,y+405),f"{side['sent_points']:.2f}",32,'#ff707a',True,'mm'); text(d,(x+cw*.75,y+405),f"{side['received_points']:.2f}",32,'#70fca1',True,'mm')
        status='PENDING' if side['status']=='pending' else f"{side['delta']:+.2f}"
        color='#f4c542' if side['status']=='pending' else ('#66ff91' if side['delta']>=0 else '#ff5964')
        text(d,(x+cw//2,y+460),status,40,color,True,'mm')
    delta=total_in-total_out; sy=370+rows*520
    if ryan:
        text(d,(W//2,sy+22),'SELF-FLEECE-O-METER',34,'white',True,'mm')
        bar=(100,sy+62,1500,sy+130); colors=['#55db56','#b7ee35','#ffe040','#ff9a32','#ff573d','#b71925']
        seg=(bar[2]-bar[0])//6
        for i,c in enumerate(colors): d.rectangle((bar[0]+i*seg,bar[1],bar[0]+(i+1)*seg,bar[3]),fill=c)
        labels=['WAIT—DID RYAN COOK?','A LITTLE SUS','OH NO…','BIG OOF','RYAN… WHY?','RYAN FLEECED RYAN']
        for i,label in enumerate(labels): text(d,(bar[0]+i*seg+seg//2,sy+154),label,13,'white',True,'mm')
        ratio=max(0,min(1,(25-delta)/125)); hx=int(bar[0]+ratio*(bar[2]-bar[0]))
        paste_circle(canvas,art('ryan_head.jpg'),(hx-48,sy+35),96,'white')
        text(d,(W//2,sy+204),f"OVERALL TRADE DIFFERENCE  {delta:+.2f} POINTS",28,'#ff666f' if delta<0 else '#65f69a',True,'mm')
    else:
        rect(d,(220,sy+25,1380,sy+185),'#090d12','#d6b34a',4,20)
        text(d,(400,sy+74),f"TRADED AWAY  {total_out:.2f}",25,'#ff6b75',True,'mm')
        text(d,(800,sy+88),f"{delta:+.2f}",66,'#66ff91' if delta>=0 else '#ff5964',True,'mm')
        text(d,(1200,sy+74),f"RECEIVED  {total_in:.2f}",25,'#70fca1',True,'mm')
        pct=(delta/total_out*100) if total_out else 0
        text(d,(800,sy+145),f"{pct:+.1f}% PRODUCTION DIFFERENCE",22,'#d6b34a',True,'mm')
    text(d,(W//2,height-18),f"THROUGH WEEK {report['through_week']}  •  AUTO-GENERATED FROM THE LIVE TRACKER",18,'#aab8c5',True,'mm')
    return canvas

def rich_veto(report):
    rows=report['vetoed_trades']; height=260+len(rows)*330+70
    canvas=Image.new('RGB',(W,height),'#080d13'); canvas.paste(art('veto_header.jpg').resize((W,260)),(0,0)); d=ImageDraw.Draw(canvas)
    for i,t in enumerate(rows):
        y=275+i*330; rect(d,(25,y,W-25,y+305),'#101318','#d6a23a',4,12); a,b=t['sides'][:2]
        text(d,(62,y+55),f"#{i+1}",46,'white',True); text(d,(55,y+102),'VETOED',24,'#ff3b45',True)
        for xx,s,col in [(220,a,'#f14d58'),(785,b,'#3ba9e8')]:
            text(d,(xx,y+30),fit(f"{s['manager']} • {s.get('team','')}",35),22,col,True)
            for j,p in enumerate(s.get('received_players',[])[:3]): player_line(canvas,d,report,p,xx,y+65+j*72,480,col)
            text(d,(xx,y+270),f"TOTAL  {s['received_points']:.2f}",31,'white',True)
        status=a['status']; delta=a['delta']; verdict='TOO EARLY TO CALL' if status=='pending' else ('VETO VINDICATED' if delta>0 else 'VETO IN QUESTION')
        color='#f4c542' if status=='pending' else ('#51f58c' if delta>0 else '#ff4d5b')
        rect(d,(1275,y+25,1550,y+280),'#10231a' if delta>0 else '#252525',color,3,14)
        text(d,(1412,y+92),verdict,20,color,True,'mm'); text(d,(1412,y+150),'PENDING' if status=='pending' else f"{abs(delta):.2f}",36,'white',True,'mm'); text(d,(1412,y+190),'POINT GAP' if status!='pending' else f"STARTS WEEK {t['first_scoring_week']}",17,'white',True,'mm')
    text(d,(W//2,height-20),f"THROUGH WEEK {report['through_week']}  •  AUTO-GENERATED FROM THE LIVE TRACKER",18,'#b8c1c9',True,'mm'); return canvas

def render_jabney(report):
    rid=report['trackers']['jabney']; trades=[]
    for trade in report['trades']:
        side=next((s for s in trade['sides'] if s.get('roster_id')==rid),None)
        if side: trades.append((trade,side))
    rows=max(1,(len(trades)+1)//2); height=470+rows*565+300
    canvas=Image.new('RGB',(W,height),'#070b12')
    header=ImageOps.fit(art('jabney_underdog_v2.jpg'),(W,450),method=Image.Resampling.LANCZOS,centering=(.5,.07))
    canvas.paste(header,(0,0))
    shade=Image.new('RGBA',(W,450),(0,0,0,0)); sd=ImageDraw.Draw(shade)
    for x in range(630,W):
        alpha=int(218*min(1,(x-630)/520)); sd.line((x,0,x,450),fill=(4,8,15,alpha))
    sd.rectangle((0,365,W,450),fill=(5,9,15,150))
    canvas.paste(Image.alpha_composite(canvas.crop((0,0,W,450)).convert('RGBA'),shade).convert('RGB'),(0,0))
    d=ImageDraw.Draw(canvas)
    d.line((0,447,W,447),fill='#c8373f',width=7)
    d.line((905,42,842,390),fill='#c8373f',width=7)
    d.line((927,42,864,390),fill='#d9aa48',width=2)
    d.polygon([(1010,42),(1530,42),(1495,85),(980,85)],fill='#b92f39')
    text(d,(1255,64),'THE LEAGUE COUNTED HIM OUT',19,'white',True,'mm')
    d.text((1260,160),'JABNEY',font=font(84,True),fill='white',anchor='mm',stroke_width=5,stroke_fill='#080b11')
    d.text((1260,236),'THE UNDERDOG',font=font(47,True),fill='#ed414b',anchor='mm',stroke_width=3,stroke_fill='#080b11')
    text(d,(1260,286),'TRADE COMEBACK TRACKER',24,'#e2b75d',True,'mm')
    text(d,(1260,337),'NO HYPE. NO SHORTCUTS. JUST KEEP FIGHTING.',16,'#eef2f5',True,'mm')
    text(d,(1260,382),'EVERY POINT IS ANOTHER STEP UP.',16,'#aebdca',True,'mm')
    total_in=total_out=0
    for i,(trade,side) in enumerate(trades):
        row,col=divmod(i,2); cw=750; x=25+col*800; y=475+row*565
        d.polygon([(x+18,y),(x+cw,y),(x+cw-18,y+18),(x,y+18)],fill='#b92f39')
        rect(d,(x,y+10,x+cw,y+530),'#101722','#8fa4b6',3,18)
        d.rectangle((x+8,y+18,x+cw-8,y+68),fill='#172433')
        text(d,(x+36,y+43),f"ROUND {i+1}",24,'#ed414b',True,'lm')
        text(d,(x+cw-30,y+43),f"SCORING FROM WEEK {trade['first_scoring_week']}",17,'#e7edf2',True,'rm')
        mid=x+cw//2; d.rectangle((x+12,y+76,mid-5,y+420),fill='#2b1118'); d.rectangle((mid+5,y+76,x+cw-12,y+420),fill='#0c2940')
        text(d,(x+cw*.25,y+101),'WHAT HE GAVE UP',17,'#ff6b73',True,'mm'); text(d,(x+cw*.75,y+101),'WHAT HE BET ON',17,'#63b8ff',True,'mm')
        for left,items,color in [(x+22,side.get('sent_players',[]),'#ff747c'),(mid+15,side.get('received_players',[]),'#6bc2ff')]:
            for j,p in enumerate(items[:5]):
                yy=y+128+j*56; paste_circle(canvas,headshot(p['player_id'],46),(left,yy),46,color)
                text(d,(left+58,yy+7),fit(player_name(report,p['player_id']),17),15,'white',True)
                text(d,(left+58,yy+29),f"{p['points']:.2f} PTS",18,color,True)
        total_in+=side['received_points']; total_out+=side['sent_points']
        text(d,(x+cw*.25,y+449),f"{side['sent_points']:.2f}",31,'#ff7078',True,'mm'); text(d,(x+cw*.75,y+449),f"{side['received_points']:.2f}",31,'#70c8ff',True,'mm')
        text(d,(x+cw*.25,y+481),'POINTS SENT',13,'#c9a8aa',True,'mm'); text(d,(x+cw*.75,y+481),'POINTS RECEIVED',13,'#9bbbd3',True,'mm')
        status='THE FIGHT CONTINUES…' if side['status']=='pending' else f"ROUND RESULT  {side['delta']:+.2f}"
        color='#f2b84b' if side['status']=='pending' else ('#66e69a' if side['delta']>=0 else '#ff626c')
        text(d,(x+cw//2,y+510),status,22,color,True,'mm')
    delta=total_in-total_out; sy=475+rows*565
    rect(d,(115,sy+20,1485,sy+245),'#0b1119','#aebdca',3,22)
    text(d,(800,sy+53),'THE COMEBACK TRAIL',25,'#e2b75d',True,'mm')
    bar=(265,sy+92,1335,sy+132); stages=['ON THE MAT','BACK ON HIS FEET','BUILDING MOMENTUM','COMEBACK COMPLETE']
    stage_colors=['#9b2832','#c85c38','#d4a642','#49b879']; seg=(bar[2]-bar[0])//4
    for j,c in enumerate(stage_colors):
        d.rectangle((bar[0]+j*seg,bar[1],bar[0]+(j+1)*seg,bar[3]),fill=c)
        text(d,(bar[0]+j*seg+seg//2,bar[3]+24),stages[j],12,'#d9e1e7',True,'mm')
    ratio=max(0.04,min(.96,(delta+100)/200)); marker=int(bar[0]+ratio*(bar[2]-bar[0]))
    d.polygon([(marker,bar[1]-18),(marker-14,bar[1]-42),(marker+14,bar[1]-42)],fill='white')
    text(d,(marker,bar[1]-54),'JABNEY',14,'white',True,'mm')
    message='THE COMEBACK IS ON' if delta>=0 else 'DOWN. NEVER OUT.'
    text(d,(800,sy+195),f"{message}   •   OVERALL TRADE DIFFERENCE  {delta:+.2f} POINTS",25,'#66e69a' if delta>=0 else '#ff626c',True,'mm')
    text(d,(W//2,height-18),f"THROUGH WEEK {report['through_week']}  •  AUTO-GENERATED FROM THE LIVE TRACKER",18,'#aab8c5',True,'mm')
    return canvas


def render_person_tracker(report, key, title, subtitle, accent):
    rid = report['trackers'][key]
    trades=[]
    for trade in report['trades']:
        side=next((s for s in trade['sides'] if s.get('roster_id')==rid),None)
        if side: trades.append((trade,side))
    im,d=base(title,subtitle,accent)
    card_w=(W-100-(len(trades)-1)*22)//max(1,len(trades)); y0=190
    total_in=total_out=0
    for i,(trade,side) in enumerate(trades):
        x=50+i*(card_w+22); rect(d,(x,y0,x+card_w,790),"#101b27",accent,3,20)
        text(d,(x+card_w//2,y0+38),f"TRADE {i+1}",32,"white",True,"mm")
        text(d,(x+card_w//2,y0+77),f"SCORING FROM WEEK {trade['first_scoring_week']}",18,"#aab8c5",True,"mm")
        mid=x+card_w//2
        d.rectangle((x+12,y0+105,mid-5,660),fill="#351118"); d.rectangle((mid+5,y0+105,x+card_w-12,660),fill="#073526")
        text(d,(x+card_w*.25,y0+130),"SENT",23,"#ff6a72",True,"mm"); text(d,(x+card_w*.75,y0+130),"RECEIVED",23,"#72ff9f",True,"mm")
        for col,items,color in [(x+24,side.get('sent_players',[]),"#ffdade"),(mid+18,side.get('received_players',[]),"#d8ffe5")]:
            for j,p in enumerate(items[:4]):
                yy=y0+180+j*95; text(d,(col,yy),fit(player_name(report,p['player_id']),16),18,color,True)
                text(d,(col,yy+34),f"{p['points']:.2f} PTS",27,"white",True)
        total_in+=side['received_points']; total_out+=side['sent_points']
        text(d,(x+card_w*.25,690),f"{side['sent_points']:.2f}",40,"#ff7079",True,"mm")
        text(d,(x+card_w*.75,690),f"{side['received_points']:.2f}",40,"#70ff9d",True,"mm")
        status="PENDING" if side['status']=='pending' else f"{side['delta']:+.2f}"
        color="#f4c542" if side['status']=='pending' else ("#66ff91" if side['delta']>=0 else "#ff5964")
        text(d,(x+card_w//2,752),status,45,color,True,"mm")
    delta=total_in-total_out
    rect(d,(300,815,1300,946),"#0a0f15",accent,4,25)
    text(d,(440,860),f"SENT  {total_out:.2f}",27,"#ff6a72",True,"mm")
    text(d,(800,854),f"{delta:+.2f}",62,"#66ff91" if delta>=0 else "#ff5964",True,"mm")
    text(d,(1140,860),f"RECEIVED  {total_in:.2f}",27,"#72ff9f",True,"mm")
    footer(d,report); return im


def render_veto(report):
    im,d=base("The Veto Vindicator","They called it a fleece. The scoreboard gets the final say.","#d6a23a","#080d13")
    rows=report['vetoed_trades'][:3]; rh=300
    for i,t in enumerate(rows):
        y=190+i*rh; rect(d,(45,y,W-45,y+270),"#101318","#d6a23a",4,16)
        text(d,(85,y+55),f"#{i+1}",52,"white",True); text(d,(85,y+110),"VETOED",29,"#ff3b45",True)
        a,b=t['sides'][:2]
        for xx,s,col in [(250,a,"#b31f2b"),(800,b,"#1268a1")]:
            text(d,(xx,y+35),fit(f"{s['manager']} / {s.get('team','')}",34),26,col,True)
            names=', '.join(player_name(report,p['player_id']) for p in s.get('received_players',[]))
            text(d,(xx,y+95),fit(names,42),25,"white",True)
            text(d,(xx,y+155),f"{s['received_points']:.2f} PTS",45,"white",True)
        status=a['status']; delta=a['delta']; verdict="TOO EARLY TO CALL" if status=='pending' else ("VETO VINDICATED" if delta>0 else "VETO IN QUESTION")
        color="#f4c542" if status=='pending' else ("#51f58c" if delta>0 else "#ff4d5b")
        text(d,(1380,y+100),verdict,24,color,True,"mm"); text(d,(1380,y+165),("PENDING" if status=='pending' else f"{abs(delta):.2f} PT GAP"),31,"white",True,"mm")
    footer(d,report); return im


def rank_rows(d, rows, y0, columns, accent, limit=None, row_height=82, box_height=68, font_size=24):
    shown = rows if limit is None else rows[:limit]
    for i,row in enumerate(shown):
        y=y0+i*row_height; fill="#172637" if i%2==0 else "#111d2a"; rect(d,(90,y,W-90,y+box_height),fill,"#30465d",1,10)
        medal=["#ffd34d","#d7e0e8","#c7834c"][i] if i<3 else "#91a4b5"
        text(d,(125,y+box_height//2),str(i+1),font_size+5,medal,True,"mm")
        x=175
        for width,getter,align,color in columns:
            val=getter(row); text(d,(x if align=='l' else x+width-10,y+box_height//2),val,font_size,color(row) if callable(color) else color,True,"lm" if align=='l' else "rm"); x+=width


def render_leaderboard(report):
    im,d=base("League Trade Leaderboard","The Rowdy War Room • Every completed deal ranked","#ff623d","#07131e")
    cols=[(330,lambda r:fit(r['manager'],21),'l','white'),(440,lambda r:fit(r['team'],30),'l','#b8c8d8'),(210,lambda r:str(r['trade_count']),'r','#dce7ef'),(250,lambda r:f"{r['delta']:+.2f}",'r',lambda r:'#62f28e' if r['delta']>=0 else '#ff6872')]
    text(d,(175,202),"MANAGER",20,"#ff8b70",True); text(d,(505,202),"TEAM",20,"#ff8b70",True); text(d,(1165,202),"TRADES",20,"#ff8b70",True); text(d,(1400,202),"TRADE +/-",20,"#ff8b70",True)
    rank_rows(d,report['leaderboard'],225,cols,"#ff623d",row_height=58,box_height=50,font_size=19); footer(d,report); return im


def render_waiver(report):
    im,d=base("Waiver Champion","Kings of the wire • Pickup production minus same-transaction drops","#f2c84b","#10100b")
    standings=report['waiver_champion']['standings']
    if standings:
        champ=standings[0]; rect(d,(85,190,1515,370),"#2a2309","#f2c84b",5,25)
        text(d,(150,230),"CURRENT CHAMPION",23,"#f2c84b",True); text(d,(150,285),champ['manager'],48,"white",True); text(d,(150,335),fit(champ['team'],38),25,"#d9cca0",True)
        text(d,(1050,255),f"{champ['points']:.2f}",72,"#f2c84b",True,"mm"); text(d,(1050,325),f"NET IMPROVEMENT  •  ${champ['faab_spent']} FAAB",22,"white",True,"mm")
    cols=[(330,lambda r:fit(r['manager'],21),'l','white'),(430,lambda r:fit(r['team'],29),'l','#d8d0ad'),(170,lambda r:str(r['claim_count']),'r','white'),(170,lambda r:f"${r['faab_spent']}",'r','white'),(220,lambda r:f"{r['points']:.2f}",'r','#f2c84b')]
    text(d,(175,407),"MANAGER",18,"#f2c84b",True); text(d,(505,407),"TEAM",18,"#f2c84b",True); text(d,(1100,407),"CLAIMS",18,"#f2c84b",True); text(d,(1275,407),"FAAB",18,"#f2c84b",True); text(d,(1440,407),"NET",18,"#f2c84b",True)
    rank_rows(d,standings,430,cols,"#f2c84b",row_height=45,box_height=39,font_size=17); footer(d,report); return im


def render_improved(report, key='rebuild_master', title='Most Improved', subtitle='Trades + net waiver/FA gains after same-transaction drops', accent='#43e6d0', bg='#07151a', leader_label='BIGGEST RISER'):
    im,d=base(title,subtitle,accent,bg)
    rows=report[key]['standings']; champ=rows[0]
    rect(d,(85,190,1515,350),'#102330',accent,5,25)
    text(d,(140,225),leader_label,22,accent,True); text(d,(140,278),champ['manager'],45,'white',True); text(d,(140,315),fit(champ['team'],40),24,'#b8cdd8',True)
    labels=[("TRADES",champ['trade_delta'],"#ff8d69"),("WAIVERS",champ['waiver_points'],"#efcf55"),("FREE AGENTS",champ['free_agent_points'],"#a98cff")]
    for i,(lab,val,col) in enumerate(labels):
        x=760+i*210; text(d,(x,235),lab,18,col,True,"mm"); text(d,(x,292),f"{val:+.2f}",35,"white",True,"mm")
    text(d,(1420,270),f"{champ['score']:+.2f}",50,accent,True,"mm"); text(d,(1420,320),"TOTAL",18,"white",True,"mm")
    cols=[(280,lambda r:fit(r['manager'],18),'l','white'),(350,lambda r:fit(r['team'],24),'l','#aac9c8'),(170,lambda r:f"{r['trade_delta']:+.1f}",'r','#ff9b7e'),(170,lambda r:f"{r['waiver_points']:.1f}",'r','#f2d56c'),(190,lambda r:f"{r['free_agent_points']:.1f}",'r','#b9a2ff'),(210,lambda r:f"{r['score']:+.2f}",'r',accent)]
    text(d,(175,390),"MANAGER / TEAM",18,accent,True); text(d,(855,390),"TRADES",18,accent,True); text(d,(1020,390),"WAIVERS",18,accent,True); text(d,(1195,390),"FREE AGENTS",18,accent,True); text(d,(1420,390),"TOTAL",18,accent,True)
    rank_rows(d,rows,410,cols,accent,row_height=46,box_height=40,font_size=17); footer(d,report); return im


def main():
    report=json.loads((ROOT/'data/report.json').read_text()); OUT.mkdir(exist_ok=True)
    jobs={
        'krunky.png':rich_person_tracker(report,'krunky','krunky_header.jpg'),
        'ryan.png':rich_person_tracker(report,'ryan','ryan_header.jpg',True),
        'jabney.png':render_jabney(report),
        'veto_vindicator.png':rich_veto(report),
        'leaderboard.png':render_leaderboard(report),
        'waiver_champion.png':render_waiver(report),
        'most_improved.png':render_improved(report),
        'rebuild_king.png':render_improved(report,'rebuild_king','Rebuild King','Who pivoted best after Week 1 • Net roster-building impact','#f4c542','#101007','CURRENT REBUILD KING'),
    }
    for name,image in jobs.items(): image.save(OUT/name,optimize=True)
    print(f"Generated {len(jobs)} visuals in {OUT.relative_to(ROOT)}/")

if __name__=='__main__': main()
