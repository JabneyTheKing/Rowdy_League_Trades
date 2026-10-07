#!/usr/bin/env python3
"""Render deterministic social graphics from data/report.json."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "visuals"
W, H = 1600, 1000
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


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


def rank_rows(d, rows, y0, columns, accent, limit=8):
    for i,row in enumerate(rows[:limit]):
        y=y0+i*82; fill="#172637" if i%2==0 else "#111d2a"; rect(d,(90,y,W-90,y+68),fill,"#30465d",1,10)
        medal=["#ffd34d","#d7e0e8","#c7834c"][i] if i<3 else "#91a4b5"
        text(d,(125,y+34),str(i+1),30,medal,True,"mm")
        x=175
        for width,getter,align,color in columns:
            val=getter(row); text(d,(x if align=='l' else x+width-10,y+34),val,24,color(row) if callable(color) else color,True,"lm" if align=='l' else "rm"); x+=width


def render_leaderboard(report):
    im,d=base("League Trade Leaderboard","The Rowdy War Room • Every completed deal ranked","#ff623d","#07131e")
    cols=[(330,lambda r:fit(r['manager'],21),'l','white'),(440,lambda r:fit(r['team'],30),'l','#b8c8d8'),(210,lambda r:str(r['scored_trades']),'r','#dce7ef'),(250,lambda r:f"{r['delta']:+.2f}",'r',lambda r:'#62f28e' if r['delta']>=0 else '#ff6872')]
    text(d,(175,202),"MANAGER",20,"#ff8b70",True); text(d,(505,202),"TEAM",20,"#ff8b70",True); text(d,(1165,202),"TRADES",20,"#ff8b70",True); text(d,(1400,202),"TRADE +/-",20,"#ff8b70",True)
    rank_rows(d,report['leaderboard'],225,cols,"#ff623d",8); footer(d,report); return im


def render_waiver(report):
    im,d=base("Waiver Champion","Kings of the wire • Production captured while owned","#f2c84b","#10100b")
    standings=report['waiver_champion']['standings']
    if standings:
        champ=standings[0]; rect(d,(85,190,1515,370),"#2a2309","#f2c84b",5,25)
        text(d,(150,230),"CURRENT CHAMPION",23,"#f2c84b",True); text(d,(150,285),champ['manager'],48,"white",True); text(d,(150,335),fit(champ['team'],38),25,"#d9cca0",True)
        text(d,(1050,255),f"{champ['points']:.2f}",72,"#f2c84b",True,"mm"); text(d,(1050,325),f"WAIVER POINTS  •  ${champ['faab_spent']} FAAB",22,"white",True,"mm")
    cols=[(330,lambda r:fit(r['manager'],21),'l','white'),(430,lambda r:fit(r['team'],29),'l','#d8d0ad'),(170,lambda r:str(r['claim_count']),'r','white'),(170,lambda r:f"${r['faab_spent']}",'r','white'),(220,lambda r:f"{r['points']:.2f}",'r','#f2c84b')]
    text(d,(175,407),"MANAGER",18,"#f2c84b",True); text(d,(505,407),"TEAM",18,"#f2c84b",True); text(d,(1100,407),"CLAIMS",18,"#f2c84b",True); text(d,(1275,407),"FAAB",18,"#f2c84b",True); text(d,(1440,407),"POINTS",18,"#f2c84b",True)
    rank_rows(d,standings,430,cols,"#f2c84b",6); footer(d,report); return im


def render_improved(report):
    im,d=base("Most Improved","Trades + waivers + free agents • Total roster-building impact","#43e6d0","#07151a")
    rows=report['rebuild_master']['standings']; champ=rows[0]
    rect(d,(85,190,1515,350),"#0b3235","#43e6d0",5,25)
    text(d,(140,225),"BIGGEST RISER",22,"#43e6d0",True); text(d,(140,278),champ['manager'],45,"white",True); text(d,(140,315),fit(champ['team'],40),24,"#a6d9d4",True)
    labels=[("TRADES",champ['trade_delta'],"#ff8d69"),("WAIVERS",champ['waiver_points'],"#efcf55"),("FREE AGENTS",champ['free_agent_points'],"#a98cff")]
    for i,(lab,val,col) in enumerate(labels):
        x=760+i*210; text(d,(x,235),lab,18,col,True,"mm"); text(d,(x,292),f"{val:+.2f}",35,"white",True,"mm")
    text(d,(1420,270),f"{champ['score']:+.2f}",50,"#43e6d0",True,"mm"); text(d,(1420,320),"TOTAL",18,"white",True,"mm")
    cols=[(280,lambda r:fit(r['manager'],18),'l','white'),(350,lambda r:fit(r['team'],24),'l','#aac9c8'),(170,lambda r:f"{r['trade_delta']:+.1f}",'r','#ff9b7e'),(170,lambda r:f"{r['waiver_points']:.1f}",'r','#f2d56c'),(190,lambda r:f"{r['free_agent_points']:.1f}",'r','#b9a2ff'),(210,lambda r:f"{r['score']:+.2f}",'r','#43e6d0')]
    text(d,(175,390),"MANAGER / TEAM",18,"#43e6d0",True); text(d,(855,390),"TRADES",18,"#43e6d0",True); text(d,(1020,390),"WAIVERS",18,"#43e6d0",True); text(d,(1195,390),"FREE AGENTS",18,"#43e6d0",True); text(d,(1420,390),"TOTAL",18,"#43e6d0",True)
    rank_rows(d,rows,410,cols,"#43e6d0",6); footer(d,report); return im


def main():
    report=json.loads((ROOT/'data/report.json').read_text()); OUT.mkdir(exist_ok=True)
    jobs={
        'krunky.png':render_person_tracker(report,'krunky','Krunky Fleece-O-Meter','Some people make trades. Krunky makes victims.','#efc343'),
        'ryan.png':render_person_tracker(report,'ryan','The Ryan Self-Fleece-O-Meter','Nobody fleeces Ryan quite like Ryan.','#f5a623'),
        'veto_vindicator.png':render_veto(report),
        'leaderboard.png':render_leaderboard(report),
        'waiver_champion.png':render_waiver(report),
        'most_improved.png':render_improved(report),
    }
    for name,image in jobs.items(): image.save(OUT/name,optimize=True)
    print(f"Generated {len(jobs)} visuals in {OUT.relative_to(ROOT)}/")

if __name__=='__main__': main()
