#!/usr/bin/env python3
"""Public voting tracker + offline Lookmhee dashboard. Read-only; no voting automation."""
import argparse, csv, datetime as dt, html, json, time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL='https://theviralhitsawards.net/categories/c66dab9ca5dc545139369cca0dc3be6e8'
FIELDS=['timestamp_utc','rank','nominee','percentage','change_pp','rank_change','gap_to_leader_pp']
TARGET='ลูกหมี ปัญญาพัชร'

def extract(page_html):
    soup=BeautifulSoup(page_html,'html.parser'); found=[]
    for card in soup.select('article[class*="ArtistCard_card"]'):
        n=card.select_one('h2[class*="ArtistCard_name"]'); p=card.select_one('[class*="ArtistCard_percentValue"]')
        if n and p:
            try: found.append({'nominee':n.get_text(' ',strip=True),'percentage':float(p.get_text(' ',strip=True).split('%')[0].strip())})
            except ValueError: pass
    return sorted(found,key=lambda x:(-x['percentage'],x['nominee']))

def history(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def team_data(path):
    if not path.exists():
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f); w.writerow(['date_thailand','active_voters','reported_free_votes','reported_special_points','notes'])
        return []
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def dashboard(rows,team,out):
    snapshots={}
    for r in rows:
        try: snapshots.setdefault(r['timestamp_utc'],[]).append({'name':r['nominee'],'pct':float(r['percentage']),'rank':int(r['rank'])})
        except (KeyError,ValueError): continue
    times=sorted(snapshots); latest=sorted(snapshots[times[-1]],key=lambda r:r['rank']) if times else []
    target=next((r for r in latest if TARGET in r['name']),None)
    runner=next((r for r in latest if r['name'] != (target or {}).get('name')),None)
    lead=round(target['pct']-runner['pct'],1) if target and runner else None
    trend=[]
    for stamp in times:
        items=snapshots[stamp]; lm=next((x for x in items if TARGET in x['name']),None)
        others=[x['pct'] for x in items if TARGET not in x['name']]
        if lm and others: trend.append({'time':stamp,'lookmhee':lm['pct'],'runner_up':max(others),'gap':round(lm['pct']-max(others),2)})
    payload={'latest':latest,'trend':trend,'team':team,'last':times[-1] if times else None,'target':target,'runner':runner,'lead':lead}
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lookmhee Voting Command Center</title><style>
    body{background:#10121c;color:#f1f1f6;font:16px system-ui,sans-serif;margin:0;padding:28px;max-width:1250px;margin:auto}h1{margin-bottom:4px}.muted{color:#a8adbe}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:24px 0}.card{background:#1d2231;border:1px solid #30384d;padding:18px;border-radius:12px}.card strong{font-size:29px;color:#f8ce62;display:block;margin-top:8px}section{background:#1d2231;border-radius:12px;padding:20px;margin:20px 0;overflow:auto}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #32384b}th{color:#f8ce62}tr.focus{background:#343023}canvas{width:100%;height:260px;display:block}.note{font-size:13px;color:#a8adbe}.badge{color:#f8ce62}a{color:#f8ce62}
    </style><h1>🏆 Lookmhee Voting Command Center</h1><div class="muted">All nominees + Lookmhee spotlight · Public percentages only · Local historical archive</div><div class="cards" id="cards"></div><section><h2>Lookmhee vs closest competitor</h2><canvas id="chart" width="1100" height="270"></canvas><p class="note">The chart tracks publicly displayed, rounded percentages. It does not represent absolute vote counts.</p></section><section><h2>Complete leaderboard</h2><table><thead><tr><th>Rank</th><th>Nominee</th><th>Vote share</th><th>Gap from leader</th></tr></thead><tbody id="leaderboard"></tbody></table></section><section><h2>Volunteer participation (optional)</h2><p class="note">Fill in team_participation.csv manually with aggregate, voluntarily reported figures. These are not verified official votes.</p><table><thead><tr><th>Thailand date</th><th>Active voters</th><th>Reported free votes</th><th>Reported special points</th><th>Notes</th></tr></thead><tbody id="team"></tbody></table></section><p class="note">Last public snapshot: <span id="updated"></span>. Refresh this file after the next tracker check. No automatic voting, account access, or vote submissions.</p>
    <script>const data=__DATA__;const fmt=x=>x===null||x===undefined?'—':x;const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));document.getElementById('updated').textContent=data.last||'No data yet';const cards=[['Lookmhee share',data.target?data.target.pct.toFixed(1)+'%':'—'],['Lookmhee rank',data.target?'#'+data.target.rank:'—'],['Nearest competitor',data.runner?data.runner.pct.toFixed(1)+'%':'—'],['Lead vs runner-up',data.lead===null?'—':data.lead.toFixed(1)+' pp'],['Nominees tracked',data.latest.length],['Historical snapshots',data.trend.length]];document.getElementById('cards').innerHTML=cards.map(([a,b])=>'<div class="card">'+esc(a)+'<strong>'+esc(b)+'</strong></div>').join('');document.getElementById('leaderboard').innerHTML=data.latest.map(x=>'<tr class="'+(x.name.includes('ลูกหมี')?'focus':'')+'"><td>'+x.rank+'</td><td>'+esc(x.name)+'</td><td>'+x.pct.toFixed(1)+'%</td><td>'+(data.latest[0].pct-x.pct).toFixed(1)+' pp</td></tr>').join('');document.getElementById('team').innerHTML=data.team.map(x=>'<tr>'+['date_thailand','active_voters','reported_free_votes','reported_special_points','notes'].map(k=>'<td>'+esc(x[k])+'</td>').join('')+'</tr>').join('');const c=document.getElementById('chart'),ctx=c.getContext('2d'),w=c.width,h=c.height,pad=35;ctx.fillStyle='#1d2231';ctx.fillRect(0,0,w,h);for(let v=0;v<=100;v+=20){let y=h-pad-(v/100)*(h-2*pad);ctx.strokeStyle='#343b4c';ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(w-pad,y);ctx.stroke();ctx.fillStyle='#b0b6c4';ctx.fillText(v+'%',2,y+4)}const t=data.trend;if(t.length){[['lookmhee','#f8ce62'],['runner_up','#81a9ed']].forEach(([k,col])=>{ctx.strokeStyle=col;ctx.lineWidth=3;ctx.beginPath();t.forEach((x,i)=>{const px=pad+(t.length===1?.5:i/(t.length-1))*(w-2*pad),py=h-pad-x[k]/100*(h-2*pad);i?ctx.lineTo(px,py):ctx.moveTo(px,py)});ctx.stroke()});ctx.fillStyle='#f8ce62';ctx.fillText('Lookmhee',pad+10,20);ctx.fillStyle='#81a9ed';ctx.fillText('Closest competitor',pad+110,20)}else{ctx.fillStyle='#fff';ctx.fillText('Run the tracker to populate history.',pad,50)}</script></html>'''
    out.write_text(page.replace('__DATA__',json.dumps(payload,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')

def check(page,path,team_path,out,debug=False):
    page.goto(URL,wait_until='domcontentloaded',timeout=45000)
    page.wait_for_selector('article[class*="ArtistCard_card"]',timeout=25000)
    page.wait_for_timeout(1500)
    content=page.content()
    if debug:
        Path('viral_hits_debug.html').write_text(content,encoding='utf-8')
        page.screenshot(path='viral_hits_debug.png',full_page=True)
    standing=extract(content)
    if not standing: print('No public percentages detected. Previous history retained.');return
    prior={r['nominee']:r for r in history(path)}
    stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    leader=standing[0]['percentage']; fresh=not path.exists() or path.stat().st_size==0
    with path.open('a',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        if fresh:writer.writeheader()
        for rank,item in enumerate(standing,1):
            old=prior.get(item['nominee']); change=round(item['percentage']-float(old['percentage']),2) if old else ''
            rank_change=int(old['rank'])-rank if old and old.get('rank') else ''
            writer.writerow({'timestamp_utc':stamp,'rank':rank,**item,'change_pp':change,'rank_change':rank_change,'gap_to_leader_pp':round(leader-item['percentage'],2)})
            print(f'{rank:>2}. {item["nominee"]}: {item["percentage"]:.1f}%'+(f' ({change:+.1f} pp)' if change!='' else ''))
    dashboard(history(path),team_data(team_path),out)
    print(f'Updated {out} | {len(standing)} nominees | {stamp}')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--interval',type=int,default=300);ap.add_argument('--once',action='store_true');ap.add_argument('--debug',action='store_true');ap.add_argument('--csv',type=Path,default=Path('viral_hits_standings.csv'));ap.add_argument('--team',type=Path,default=Path('team_participation.csv'));ap.add_argument('--dashboard',type=Path,default=Path('lookmhee_dashboard.html'));a=ap.parse_args()
    if not a.once and a.interval<300:ap.error('Minimum interval is 300 seconds.')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page(locale='th-TH')
        try:
            while True:
                try:check(page,a.csv,a.team,a.dashboard,a.debug)
                except Exception as e:print('Check failed:',e)
                if a.once:break
                time.sleep(a.interval)
        except KeyboardInterrupt:print('\nStopped.')
        finally:browser.close()
if __name__=='__main__':main()
