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
    payload={'latest':latest,'trend':trend,'team':team,'last':times[-1] if times else None,'target':target,'runner':runner,'lead':lead,'history_by_time':{stamp:{'sonya':next((x['pct'] for x in items if 'ซอนญ่า' in x['name']),None)} for stamp,items in snapshots.items()}}
    page=Path(__file__).with_name('dashboard_template.html').read_text(encoding='utf-8')
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
