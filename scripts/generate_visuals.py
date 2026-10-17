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
    text(d, (W//2, H-26), f"THROUGH WEEK {report['through_week']}{' (PARTIAL)' if report.get('partial_week') else ''}  •  TRANSACTIONS SINCE AUGUST 23, 2026  •  AUTO-GENERATED", 20, "#aab8c5", True, "mm")
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
    text(d,(W//2,height-18),f"THROUGH WEEK {report['through_week']}{' (PARTIAL)' if report.get('partial_week') else ''}  •  AUTO-GENERATED FROM THE LIVE TRACKER",18,'#aab8c5',True,'mm')
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
        status=a['status']; delta=a['delta']; verdict='TOO EARLY TO CALL' if status=='pending' else ('EVEN SO FAR' if delta == 0 else ('VETO VINDICATED' if delta>0 else 'VETO IN QUESTION'))
        color='#f4c542' if status=='pending' else ('#51f58c' if delta>0 else '#ff4d5b')
        rect(d,(1275,y+25,1550,y+280),'#10231a' if delta>0 else '#252525',color,3,14)
        text(d,(1412,y+92),verdict,20,color,True,'mm'); text(d,(1412,y+150),'PENDING' if status=='pending' else f"{abs(delta):.2f}",36,'white',True,'mm'); text(d,(1412,y+190),'POINT GAP' if status!='pending' else f"STARTS WEEK {t['first_scoring_week']}",17,'white',True,'mm')
    text(d,(W//2,height-20),f"THROUGH WEEK {report['through_week']}{' (PARTIAL)' if report.get('partial_week') else ''}  •  AUTO-GENERATED FROM THE LIVE TRACKER",18,'#b8c1c9',True,'mm'); return canvas

def render_jabney(report):
    rid=report['trackers']['jabney']; trades=[]
    for trade in report['trades']:
        side=next((s for s in trade['sides'] if s.get('roster_id')==rid),None)
        if side: trades.append((trade,side))
    waivers=[row for row in report['waiver_champion']['claims'] if row['roster_id']==rid]
    free_agents=[row for row in report['rebuild_master']['free_agent_pickups'] if row['roster_id']==rid]
    improvement=next(row for row in report['rebuild_master']['standings'] if row['roster_id']==rid)
    rows=max(1,(len(trades)+1)//2)
    waiver_height=94+((len(waivers)+1)//2)*96
    free_agent_height=94+((len(free_agents)+1)//2)*96
    height=470+rows*565+waiver_height+free_agent_height+530
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
    trade_delta=total_in-total_out

    def pickup_section(title, subtitle, items, y, accent, total):
        text(d,(55,y+33),title,30,accent,True,'lm')
        text(d,(55,y+62),subtitle,14,'#aebdca',True,'lm')
        text(d,(1545,y+40),f"{len(items)} MOVES  •  NET {total:+.2f}",22,accent,True,'rm')
        d.line((45,y+78,1555,y+78),fill=accent,width=3)
        for i,item in enumerate(items):
            row,col=divmod(i,2); x=25+col*800; yy=y+92+row*96; cw=750
            rect(d,(x,yy,x+cw,yy+82),'#101722','#334657',2,12)
            paste_circle(canvas,headshot(item['player_id'],46),(x+14,yy+15),46,accent)
            add_name=fit(player_name(report,item['player_id']),20)
            text(d,(x+74,yy+17),f"ADD  {add_name}",16,'white',True)
            text(d,(x+74,yy+43),f"{item['pickup_points']:.2f} PTS",15,accent,True)
            drop=item.get('dropped_player_id')
            drop_name=fit(player_name(report,drop),18) if drop else 'NO ASSOCIATED DROP'
            drop_color='#ff747c' if drop else '#7f91a0'
            text(d,(x+310,yy+17),f"DROP  {drop_name}" if drop else drop_name,14,drop_color,True)
            text(d,(x+310,yy+43),f"-{item['dropped_points']:.2f} PTS" if drop else 'STANDALONE DROPS IGNORED',13,drop_color,True)
            status='PENDING' if item['status']=='pending' else f"{item['points']:+.2f}"
            score_color='#f2b84b' if item['status']=='pending' else ('#66e69a' if item['points']>=0 else '#ff626c')
            text(d,(x+cw-24,yy+28),status,25,score_color,True,'rm')
            window=f"W{item['first_week']}–{item['last_week']}"
            state='RELEASED' if item['released'] else ('UPCOMING' if item['status']=='pending' else 'ACTIVE')
            faab=f"  •  ${item['faab']} FAAB" if item['faab'] else ''
            text(d,(x+cw-24,yy+58),f"{window}  •  {state}{faab}",11,'#91a4b5',True,'rm')
        return y+94+((len(items)+1)//2)*96

    sy=475+rows*565
    sy=pickup_section('WAIVER WIRE BATTLES','PICKUP PRODUCTION MINUS THE PLAYER DROPPED IN THE SAME MOVE',waivers,sy,'#e2b75d',improvement['waiver_points'])
    sy=pickup_section('FREE AGENCY FINDS','EVERY ADD COUNTS ONLY WHILE JABNEY OWNS THE PLAYER',free_agents,sy,'#63b8ff',improvement['free_agent_points'])

    combined=improvement['score']
    scored_waivers=[row for row in waivers if row['status']=='scored']
    scored_free_agents=[row for row in free_agents if row['status']=='scored']
    waiver_added=round(sum(row['pickup_points'] for row in scored_waivers),2)
    waiver_dropped=round(sum(row['dropped_points'] for row in scored_waivers),2)
    free_agent_added=round(sum(row['pickup_points'] for row in scored_free_agents),2)
    free_agent_dropped=round(sum(row['dropped_points'] for row in scored_free_agents),2)
    all_added=round(total_in+waiver_added+free_agent_added,2)
    all_baseline=round(total_out+waiver_dropped+free_agent_dropped,2)

    text(d,(800,sy+24),'TOTAL IMPACT',27,'#e2b75d',True,'mm')
    impact=[
        ('TRADES','RECEIVED',total_in,'SENT',total_out,trade_delta,'#ed414b'),
        ('WAIVERS','PICKUPS',waiver_added,'DROPS',waiver_dropped,improvement['waiver_points'],'#e2b75d'),
        ('FREE AGENCY','PICKUPS',free_agent_added,'DROPS',free_agent_dropped,improvement['free_agent_points'],'#63b8ff'),
        ('ALL MOVES','PRODUCTION',all_added,'BASELINE',all_baseline,combined,'#66e69a' if combined>=0 else '#ff626c'),
    ]
    for i,(label,in_label,in_value,out_label,out_value,net,accent) in enumerate(impact):
        x=25+i*395
        rect(d,(x,sy+48,x+365,sy+178),'#101722',accent,3,14)
        text(d,(x+182,sy+71),label,18,accent,True,'mm')
        text(d,(x+28,sy+100),f"{in_label}  {in_value:.2f}",13,'#d9e1e7',True)
        text(d,(x+28,sy+123),f"{out_label}  {out_value:.2f}",13,'#aebdca',True)
        text(d,(x+337,sy+115),f"{net:+.2f}",28,'#66e69a' if net>=0 else '#ff626c',True,'rm')
        text(d,(x+337,sy+145),'NET IMPACT',11,'#91a4b5',True,'rm')
    sy+=205

    rect(d,(115,sy+20,1485,sy+275),'#0b1119','#aebdca',3,22)
    text(d,(800,sy+53),'THE COMEBACK TRAIL',25,'#e2b75d',True,'mm')
    text(d,(800,sy+86),f"TRADES {trade_delta:+.2f}   •   WAIVERS {improvement['waiver_points']:+.2f}   •   FREE AGENTS {improvement['free_agent_points']:+.2f}",16,'#d9e1e7',True,'mm')
    bar=(265,sy+112,1335,sy+152); stages=['ON THE MAT','BACK ON HIS FEET','BUILDING MOMENTUM','COMEBACK COMPLETE']
    stage_colors=['#9b2832','#c85c38','#d4a642','#49b879']; seg=(bar[2]-bar[0])//4
    for j,c in enumerate(stage_colors):
        d.rectangle((bar[0]+j*seg,bar[1],bar[0]+(j+1)*seg,bar[3]),fill=c)
        text(d,(bar[0]+j*seg+seg//2,bar[3]+24),stages[j],12,'#d9e1e7',True,'mm')
    ratio=max(0.04,min(.96,(combined+100)/200)); marker=int(bar[0]+ratio*(bar[2]-bar[0]))
    d.polygon([(marker,bar[1]-18),(marker-14,bar[1]-42),(marker+14,bar[1]-42)],fill='white')
    text(d,(marker,bar[1]+20),'JABNEY',11,'white',True,'mm')
    message='THE COMEBACK IS ON' if combined>=0 else 'DOWN. NEVER OUT.'
    text(d,(800,sy+225),f"{message}   •   OVERALL ROSTER IMPROVEMENT  {combined:+.2f} POINTS",25,'#66e69a' if combined>=0 else '#ff626c',True,'mm')
    text(d,(W//2,height-18),f"THROUGH WEEK {report['through_week']}{' (PARTIAL)' if report.get('partial_week') else ''}  •  AUTO-GENERATED FROM THE LIVE TRACKER",18,'#aab8c5',True,'mm')
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
        status=a['status']; delta=a['delta']; verdict="TOO EARLY TO CALL" if status=='pending' else ("EVEN SO FAR" if delta == 0 else ("VETO VINDICATED" if delta>0 else "VETO IN QUESTION"))
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


def render_conner_metcalf(report):
    c = report['conner_metcalf']; waiting = c['status'] != 'active'
    im = Image.new('RGB', (W, H), '#070c14'); d = ImageDraw.Draw(im)
    for x in range(0, W, 80):
        d.line((x, 0, x-400, H), fill='#152335', width=2)
    d.polygon([(0,180),(770,180),(650,720),(0,720)],fill='#132b48')
    d.polygon([(830,180),(W,180),(W,720),(710,720)],fill='#39121e')
    text(d,(800,65),'THE RETURN MATCHUP',59,'white',True,'mm')
    text(d,(800,125),'DK METCALF  vs.  JAMES CONNER',31,'#dfb65b',True,'mm')
    for x,pid,name,color,points in [(390,'5846','DK METCALF','#65bdff',c['metcalf_points']),
                                   (1210,'4137','JAMES CONNER','#ff6979',c['conner_points'])]:
        portrait = headshot(pid,240)
        paste_circle(im,portrait,(x-120,215),240,color)
        if all(lo == hi for lo, hi in portrait.getextrema()):
            text(d,(x,335),'DK' if pid == '5846' else 'JC',80,color,True,'mm')
        text(d,(x,508),name,39,'white',True,'mm')
        text(d,(x,601),f'{points:.2f}',88,color,True,'mm')
        text(d,(x,673),'FANTASY POINTS',21,'#becbd8',True,'mm')
    text(d,(800,415),'VS',63,'#dfb65b',True,'mm')
    rect(d,(95,750,1505,918),'#101722','#dfb65b',3,18)
    title = 'WAITING FOR CONNER’S RETURN' if waiting else f"DK ADVANTAGE  {c['delta']:+.2f} POINTS"
    text(d,(800,790),title,34,'#dfb65b',True,'mm')
    note = 'BOTH COUNTERS LOCKED AT ZERO' if waiting else f"BOTH COUNTERS STARTED WEEK {c['first_scoring_week']}"
    text(d,(800,837),note,23,'white',True,'mm')
    text(d,(800,881),'Same starting week • Conner’s return game included • No earlier points',19,'#aab8c5',True,'mm')
    text(d,(800,970),f"THROUGH WEEK {report['through_week']} • AUTO-UPDATED EVERY SIX HOURS",20,'#aab8c5',True,'mm')
    return im


def advanced_header(key, title, subtitle, height):
    canvas = Image.new('RGB', (W, height), '#080e17')
    d = ImageDraw.Draw(canvas)
    if key == 'gibbs_of_war':
        import math
        d.rectangle((0,0,W,354),fill='#151b22')
        for x in range(-300,W,95):
            d.line((x,0,x+240,354),fill='#263039',width=4)
        d.polygon([(0,0),(390,0),(280,354),(0,354)],fill='#8a252d')
        d.polygon([(1230,0),(W,0),(W,354),(1110,354)],fill='#8a252d')
        cx,cy=205,177
        gear=[]
        for i in range(72):
            theta=i*math.pi/36;radius=130 if i%4 in (0,1) else 111
            gear.append((cx+radius*math.cos(theta),cy+radius*math.sin(theta)))
        d.polygon(gear,fill='#d2d9dd')
        d.ellipse((cx-86,cy-86,cx+86,cy+86),fill='#17232d')
        text(d,(cx,cy),'GW',63,'#e9edf0',True,'mm')
        text(d,(875,117),'GIBBS OF WAR',83,'#f1f3f5',True,'mm')
        text(d,(875,211),'THE WAR ROOM',37,'#ff7f82',True,'mm')
        text(d,(875,276),'TEAM BUILDING • LINEUP IMPACT • EVERY MOVE COUNTS',20,'#c6d2db',True,'mm')
        accent='#f77c82'
    else:
        header = 'jabney_underdog_v2.jpg' if key == 'jabney' else 'krunky_header.jpg'
        banner = ImageOps.fit(art(header), (W, 354), method=Image.Resampling.LANCZOS, centering=(.5,.07))
        canvas.paste(banner, (0, 0))
        accent = '#5ccfea' if key == 'jabney' else '#ecc356'
    display_name = 'Gibbs of War' if key == 'gibbs_of_war' else key
    d.rectangle((0, 354, W, 466), fill='#101c2a')
    text(d, (800, 389), (display_name + ' • ' + title).upper(), 40 if key == 'gibbs_of_war' or title.startswith('INJURY') else 44, accent, True, 'mm')
    text(d, (800, 440), subtitle, 20, '#d6e2ef', True, 'mm')
    return canvas, d, accent


def advanced_footer(d, report, y, note):
    text(d, (800, y), note, 20, '#b8c9da', False, 'mm')
    text(d, (800, y+35), f"THROUGH WEEK {report['through_week']}" + (' • PARTIAL / PROVISIONAL' if report.get('partial_week') else ' • COMPLETE') + ' • TRADES SINCE AUGUST 23', 20, '#b8c9da', True, 'mm')


def render_positional(report, key):
    p = report['positional_value'][key]
    rows = p['moves']
    height = 890 + max(1,len(rows))*72
    im, d, accent = advanced_header(key, 'POSITIONAL VALUE',
        'Performance above the weekly positional benchmark • A separate view from raw points', height)
    for i, c in enumerate(p['components']):
        x = 45 + i*505
        rect(d, (x,485,x+485,588), '#142538', accent, 2, 14)
        text(d, (x+24,513), c['label'].upper(), 21, accent, True)
        text(d, (x+24,555), f"RAW {c['raw']:+.2f}", 23, 'white', True)
        text(d, (x+465,555), f"ADJ {c['adjusted']:+.2f}", 27, '#6cf3a0' if c['adjusted']>=0 else '#ff8390', True,'ra')
    y=625
    for x,label in [(48,'MOVE'),(265,'RECEIVED / ADDED'),(660,'SENT / DROPPED'),(1215,'RAW NET'),(1515,'POSITIONAL NET')]:
        text(d,(x,y),label,19,accent,True,'ra' if x>1200 else None)
    for i,row in enumerate(rows):
        yy=660+i*72
        rect(d,(35,yy-10,1565,yy+53),'#132033' if i%2==0 else '#0e1827',None,1,8)
        text(d,(50,yy+14),fit(row['label'],23),19,'#c1d1e0',True,'lm')
        for x,field in [(265,'received'),(660,'sent')]:
            names=[player_name(report,pid) for pid in row[field]]
            # Split into up to two lines; full names and assets remain in the companion report.
            label=', '.join(names) or '—'
            if len(label)>32:
                text(d,(x,yy+2),fit(label[:32],32),17,'white')
                text(d,(x,yy+25),fit(label[32:],32),17,'white')
            else:
                text(d,(x,yy+14),label,18,'white',False,'lm')
        text(d,(1215,yy+14),f"{row['raw']:+.2f}",25,'#cad8e6',True,'rm')
        label='PENDING' if row['status']=='pending' else f"{row['adjusted']:+.2f}"
        text(d,(1515,yy+14),label,28,'#6cf3a0' if row['adjusted']>=0 else '#ff8390',True,'rm')
    y=660+max(1,len(rows))*72
    rect(d,(35,y,1565,y+100),'#1a2b3a',accent,3,12)
    text(d,(65,y+29),'TOTAL POSITIONAL IMPACT',26,accent,True)
    text(d,(65,y+68),'Byes / missed games = 0 • Active below-average games can be negative',19,'#c5d1db')
    text(d,(1515,y+48),f"{p['total']:+.2f}",61,'#6cf3a0' if p['total']>=0 else '#ff8390',True,'rm')
    advanced_footer(d,report,y+139,'Weekly top-player averages: QB 12 • RB 30 • WR 42 • TE 12 • K 12 • DEF 12')
    return im


def render_draft_vs_trades(report, key):
    c=report['draft_vs_trades'][key]
    weeks=c['weeks']; latest=weeks[-1] if weeks else None
    height=1680+len(weeks)*56
    im,d,accent=advanced_header(key,'DRAFT vs. TRADES',
        'Your best legal starting lineup each week • Original draft versus trades-only roster',height)
    for i,(label,value,color) in enumerate([('DRAFTED TEAM',c['draft_total'],'#c8d6e7'),('AFTER TRADES',c['trade_total'],accent),('TRADING IMPACT',c['delta'],'#6cf3a0' if c['delta']>=0 else '#ff8390')]):
        x=40+i*510
        rect(d,(x,490,x+495,626),'#142538',color,2,14)
        text(d,(x+247,523),label,23,color,True,'mm')
        text(d,(x+247,582),f'{value:+.2f}' if i==2 else f'{value:.2f}',49,'white',True,'mm')
    text(d,(800,664),'WEEKLY BEST-LINEUP COMPARISON',28,accent,True,'mm')
    for x,label in [(75,'WEEK'),(670,'DRAFTED'),(1090,'AFTER TRADES'),(1500,'IMPACT')]:
        text(d,(x,706),label,20,'#b8cbde',True,'ra' if x>100 else None)
    for i,row in enumerate(weeks):
        y=750+i*56
        rect(d,(40,y-16,1560,y+31),'#142235',None,1,7)
        text(d,(75,y+7),str(row['week']),24,'white',True,'lm')
        for x,value in [(670,row['drafted']['points']),(1090,row['traded']['points']),(1500,row['delta'])]:
            text(d,(x,y+7),f'{value:+.2f}' if x==1500 else f'{value:.2f}',26,('#6cf3a0' if value>=0 else '#ff8390') if x==1500 else 'white',True,'rm')
    y=765+len(weeks)*56
    if latest:
        text(d,(800,y+18),f"WEEK {latest['week']} • OPTIMAL STARTERS",29,accent,True,'mm')
        text(d,(390,y+65),'ORIGINAL DRAFT',22,'#cbd9e9',True,'mm')
        text(d,(1190,y+65),'DRAFT + TRADES',22,accent,True,'mm')
        for i,(a,b) in enumerate(zip(latest['drafted']['lineup'],latest['traded']['lineup'])):
            yy=y+102+i*46
            for x,item in [(40,a),(830,b)]:
                rect(d,(x,yy-12,x+730,yy+28),'#132033',None,1,6)
                text(d,(x+12,yy+8),item['slot'],18,accent,True,'lm')
                text(d,(x+105,yy+8),fit(player_name(report,item['player_id']) if item['player_id'] else 'Empty slot',29),21,'white',True,'lm')
                text(d,(x+710,yy+8),f"{item['points']:.2f}",23,'#cbd9e9',True,'rm')
    method_y=height-300
    rect(d,(35,method_y,1565,method_y+185),'#142538',accent,2,12)
    text(d,(65,method_y+22),'METHODOLOGY',25,accent,True)
    for i,line in enumerate([
        'Compare the original draft with that draft adjusted only for eligible trades since August 23.',
        'Optimize all 10 legal starting slots separately each week using league scoring; one player per slot.',
        'Ignore actual wire moves; fill uncovered slots with the mean of top 5 available waiver players by position.',
        'Sum weekly lineup differences. Hindsight potential, not actual start / sit results; picks remain unvalued.',
    ]):
        text(d,(65,method_y+64+i*28),line,21,'#d0dce7')
    advanced_footer(d,report,height-83,'Rostered starters first • Temporary waiver coverage for holes • No later trades applied to earlier weeks')
    return im


def render_team_impact(report,key):
    c=report['team_impact'][key]; t=c['totals']; weeks=c['weeks']
    height=2070+len(weeks)*56
    im,d,accent=advanced_header(key,'TEAM IMPACT',
        'Drafted team vs. rebuilt team • Optimal lineups isolate trade impact with wire moves held fixed',height)
    for i,(field,label) in enumerate([('drafted','ORIGINAL DRAFT'),('trades_only','TRADES ONLY'),('wire_only','WAIVERS + FA ONLY'),('all_moves','ALL MOVES')]):
        x=35+i*392
        rect(d,(x,490,x+376,625),'#142538',accent,2,13)
        text(d,(x+188,525),label,21,accent,True,'mm')
        text(d,(x+188,583),f"{t[field]:.2f}",46,'white',True,'mm')
    for i,(field,label,note) in enumerate([('wire_impact','WIRE IMPACT','Wire-only minus draft'),('trade_impact','TRADE IMPACT','All moves minus wire-only'),('total_impact','TOTAL IMPROVEMENT','All moves minus draft')]):
        x=35+i*525; value=t[field]; color='#6cf3a0' if value>=0 else '#ff8390'
        rect(d,(x,649,x+505,807),'#172939',color,3,14)
        text(d,(x+252,679),label,23,color,True,'mm')
        text(d,(x+252,735),f'{value:+.2f}',53,'white',True,'mm')
        text(d,(x+252,781),note,20,'#bdcfe0',False,'mm')
    text(d,(800,844),f"Trades alone: {t['trade_only_impact']:+.2f}  •  Trade / wire interaction: {t['interaction']:+.2f} (included in trade impact)",23,accent,True,'mm')
    text(d,(800,882),'Trade impact + wire impact = total improvement. No bench points or double-counted lineup gains.',20,'#c4d1df',False,'mm')
    cols=[(80,'WK'),(315,'DRAFT'),(555,'TRADES ONLY'),(795,'WIRE ONLY'),(1035,'ALL MOVES'),(1280,'WIRE +/-'),(1520,'TRADE +/-')]
    for x,label in cols: text(d,(x,936),label,19,accent,True,'rm')
    for i,row in enumerate(weeks):
        y=977+i*56
        rect(d,(35,y-20,1565,y+28),'#142235',None,1,8)
        vals=[row['week']]+[row[f]['points'] for f in ('drafted','trades_only','wire_only','all_moves')]+[row['wire_impact'],row['trade_impact']]
        for j,((x,_),value) in enumerate(zip(cols,vals)):
            label=str(value) if j==0 else (f'{value:+.2f}' if j>4 else f'{value:.2f}')
            text(d,(x,y+5),label,24,('#6cf3a0' if value>=0 else '#ff8390') if j>4 else 'white',True,'rm')
    y=992+len(weeks)*56
    if weeks:
        latest=weeks[-1]
        text(d,(800,y+14),f"WEEK {latest['week']} • TRADE IMPACT IN THE STARTING LINEUP",28,accent,True,'mm')
        text(d,(395,y+63),'WITHOUT TRADES • WIRE MOVES INCLUDED',20,'#c6d8e9',True,'mm')
        text(d,(1190,y+63),'WITH TRADES • ALL MOVES INCLUDED',20,accent,True,'mm')
        for i,(a,b) in enumerate(zip(latest['wire_only']['lineup'],latest['all_moves']['lineup'])):
            yy=y+102+i*46
            for x,item in [(40,a),(830,b)]:
                rect(d,(x,yy-12,x+730,yy+28),'#132033',None,1,6)
                text(d,(x+12,yy+8),item['slot'],18,accent,True,'lm')
                text(d,(x+105,yy+8),fit(player_name(report,item['player_id']) if item['player_id'] else 'Empty slot',29),21,'white',True,'lm')
                text(d,(x+710,yy+8),f"{item['points']:.2f}",23,'#cbd9e9',True,'rm')
    method_y = height-450
    rect(d,(35,method_y,1565,method_y+330),'#142538',accent,2,12)
    text(d,(65,method_y+30),'METHODOLOGY',26,accent,True)
    rules = [
        '1. Start with the draft; replay eligible moves since August 23. Later moves never change earlier weeks.',
        '2. Use participating rostered players first in 10 legal slots; each player fills one slot. No bench points.',
        '3. Fill holes with mean points of top 5 available waiver players by position, excluding held / uncleared players.',
        '4. Wire impact = wire-only minus draft. Trade impact = all moves minus wire-only. Their sum is total gain.',
        '5. Trade impact includes trade / wire interaction. The same recorded wire decisions are held fixed.',
        '6. Coverage is temporary and hindsight-based, not top-12/24 averages. No claim, budget or roster-cap simulation.',
        '7. No cover until a week is complete. Same rule for all scenarios; weekly waiver samples are listed in the report.',
    ]
    for i,line in enumerate(rules):
        text(d,(65,method_y+80+i*33),line,21,'#d0dce7')
    advanced_footer(d,report,height-83,'Hindsight-optimal legal lineups • Departed players removed • Full weekly breakdown in report')
    return im


def render_injury_adjusted(report,key):
    c=report['injury_adjusted'][key];rows=c['adjustments'];weeks=c['weeks']
    height=1550+len(weeks)*54+max(1,len(rows))*49
    im,d,accent=advanced_header(key,'INJURY-ADJUSTED IMPACT',
        'A separate injury estimate • Temporary waiver coverage in both comparisons • Reoptimized lineups',height)
    text(d,(800,502),'BASELINE WITH WAIVER COVER vs. INJURY ESTIMATE',27,accent,True,'mm')
    for x,label in [(60,'METRIC'),(810,'BASELINE + COVER'),(1190,'ADJUSTED ESTIMATE'),(1520,'CHANGE')]:
        text(d,(x,552),label,19,'#b9cddd',True,'rm' if x>100 else 'lm')
    for i,(field,label) in enumerate([('trade_impact','TRADE IMPACT'),('wire_impact','WAIVER / FA IMPACT'),('total_impact','TOTAL TEAM IMPROVEMENT')]):
        y=600+i*72
        rect(d,(35,y-23,1565,y+37),'#152639',accent if i==2 else None,2,10)
        text(d,(60,y+5),label,25,'white',True,'lm')
        for x,value in [(810,c['actual_totals'][field]),(1190,c['totals'][field]),(1520,c['injury_swing'][field])]:
            text(d,(x,y+5),f'{value:+.2f}',34,'#6cf3a0' if value>=0 else '#ff8390',True,'rm')
    text(d,(800,829),f"{len(rows)} player-weeks estimated • {len(c['insufficient_baselines'])} confirmed absences lack a baseline",24,accent,True,'mm')
    text(d,(800,865),f"{len(c['other_absences'])} other zero-participation games unchanged • Injury evidence is deliberately limited",20,'#c1cfdb',False,'mm')
    if c['source_errors']:
        text(d,(800,902),'SOURCE RETRIEVAL WARNING — cached / partial evidence; see report',22,'#ffc759',True,'mm')
    else:
        text(d,(800,902),'Estimates may improve either side of a trade; an adjustment is not automatically a credit.',20,'#c1cfdb',False,'mm')
    cols=[(85,'WK'),(520,'BASELINE TRADE +/-'),(1000,'ADJ. TRADE +/-'),(1510,'ADJ. TOTAL GAIN')]
    for x,label in cols:text(d,(x,950),label,20,accent,True,'rm')
    actual=report['team_impact'][key]['weeks']
    for i,(row,original) in enumerate(zip(weeks,actual)):
        y=990+i*54
        rect(d,(35,y-19,1565,y+27),'#142235',None,1,7)
        for j,((x,_),value) in enumerate(zip(cols,[row['week'],original['trade_impact'],row['trade_impact'],row['total_impact']])):
            text(d,(x,y+4),str(value) if j==0 else f'{value:+.2f}',25,'white',True,'rm')
    y=1000+len(weeks)*54
    text(d,(800,y+25),'PLAYER-WEEKS REPLACED WITH AN ESTIMATE',26,accent,True,'mm')
    for x,label in [(75,'WK'),(170,'PLAYER'),(890,'ACTUAL'),(1180,'ESTIMATE'),(1510,'PRIOR GAMES')]:
        text(d,(x,y+68),label,19,'#b9cddd',True,'rm' if x>800 else 'lm')
    for i,row in enumerate(rows):
        yy=y+111+i*49
        rect(d,(35,yy-16,1565,yy+26),'#142235',None,1,7)
        text(d,(75,yy+5),str(row['week']),22,'white',True,'lm')
        text(d,(170,yy+5),fit(player_name(report,row['player_id']),34),23,'white',True,'lm')
        for x,label in [(890,f"{row['actual']:.2f}"),(1180,f"{row['estimated']:.2f}"),(1510,str(len(row['sample'])))]:
            text(d,(x,yy+5),label,24,'#d3e1ec',True,'rm')
    if not rows:text(d,(800,y+115),'No supported player-week estimates yet; actual results retained.',22,'white',False,'mm')
    method_y=y+150+max(1,len(rows))*49
    rect(d,(35,method_y,1565,method_y+350),'#142538',accent,2,12)
    text(d,(65,method_y+28),'METHODOLOGY • LIMITED INJURY ESTIMATE',25,accent,True)
    rules=[
        '1. Same weekly draft / trades / wire / all-moves rosters, eligibility rules and August 23 transaction cutoff.',
        '2. Replace only completed-game absences: zero participation plus NFL injury OUT or documented first-four-game IR.',
        '3. Estimate = mean league points in 2+ earlier participating games with no archived weekly injury listing.',
        '4. Reoptimize all 10 legal starting slots in every scenario. Backups count; no bench points or duplicated players.',
        '5. Wire impact = wire-only minus draft; trade impact = all moves minus wire-only, including their interaction.',
        '6. After eligible injury estimates, fill remaining holes with mean points of top 5 available waiver players by position.',
        '7. Rostered starters first; no injury estimate plus waiver credit in the same slot. No cover during partial weeks.',
        '8. Waiver cover is hindsight-based, not top-12/24 averages. Fixed moves; no cap/budget simulation. Samples in report.',
    ]
    for i,line in enumerate(rules):text(d,(65,method_y+78+i*31),line,20,'#d0dce7')
    # Content height is derived from the panels so it cannot collide with the footer.
    bottom=method_y+440
    if bottom>im.height:
        expanded=Image.new('RGB',(W,bottom),'#080e17');expanded.paste(im,(0,0));im=expanded;d=ImageDraw.Draw(im)
    advanced_footer(d,report,im.height-65,'NFL injury reports + dated reserve placements • ESTIMATES, NOT ACTUAL SCORES')
    return im


def main():
    report=json.loads((ROOT/'data/report.json').read_text()); OUT.mkdir(exist_ok=True)
    jobs={
        'metcalf_vs_conner.png':render_conner_metcalf(report),
        'krunky.png':rich_person_tracker(report,'krunky','krunky_header.jpg'),
        'ryan.png':rich_person_tracker(report,'ryan','ryan_header.jpg',True),
        'jabney.png':render_jabney(report),
        'veto_vindicator.png':rich_veto(report),
        'leaderboard.png':render_leaderboard(report),
        'waiver_champion.png':render_waiver(report),
        'most_improved.png':render_improved(report),
        'rebuild_king.png':render_improved(report,'rebuild_king','Rebuild King','Who pivoted best after Week 1 • Net roster-building impact','#f4c542','#101007','CURRENT REBUILD KING'),
    }
    for key in ('jabney', 'krunky'):
        jobs[f'{key}_positional.png'] = render_positional(report, key)
        jobs[f'{key}_draft_vs_trades.png'] = render_draft_vs_trades(report, key)
    for key in report['team_impact']:
        jobs[f'{key}_team_impact.png'] = render_team_impact(report, key)
        jobs[f'{key}_injury_adjusted.png'] = render_injury_adjusted(report, key)
    # Stamp every render and publish a single mutable gallery with fresh image URLs.
    stamp = report['updated_at'][:19].replace('T', ' ') + ' UTC'
    version = ''.join(c for c in report['updated_at'] if c.isdigit())
    gallery = ['# Latest Tracker Visuals', '', f'Updated {stamp}. Through Week {report["through_week"]}' +
               (' (partial).' if report.get('partial_week') else ' (complete).'), '',
               'Bookmark this page for the latest images. Links to specific commits are frozen snapshots.', '']
    for name, image in jobs.items():
        output = Image.new('RGB', (image.width, image.height + 38), '#070c12')
        output.paste(image, (0, 0))
        text(ImageDraw.Draw(output), (image.width//2, image.height+19),
             f'REFRESHED {stamp}', 16, '#aab8c5', True, 'mm')
        output.save(OUT/name,optimize=True)
        title = name.removesuffix('.png').replace('_', ' ').title()
        url = f'https://raw.githubusercontent.com/JabneyTheKing/Rowdy_League_Trades/main/visuals/{name}?v={version}'
        gallery += [f'## {title}', '', f'[Open full-size image]({url})', '', f'![{title}]({url})', '']
    (ROOT/'reports/latest_visuals.md').write_text('\n'.join(gallery) + '\n')
    print(f"Generated {len(jobs)} visuals in {OUT.relative_to(ROOT)}/")

if __name__=='__main__': main()
