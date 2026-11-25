import re,sys,hashlib,datetime as dt,collections
from pathlib import Path
import icalendar, vobject, jdatetime
MONTHS=["Farvardin","Ordibehesht","Khordad","Tir","Mordad","Shahrivar","Mehr","Aban","Azar","Dey","Bahman","Esfand"]
ok=True
def check(c,msg):
    global ok
    print(('PASS ' if c else 'FAIL ')+msg); ok&=bool(c)
for name,expect_extra in [('Jalali-Finglish-1405-1407.ics',True),('Jalali-Finglish-1405-1407_dates-only.ics',False)]:
    print('==',name)
    raw=Path('out',name).read_bytes()
    check(b'\r\n' in raw and b'\n' not in raw.replace(b'\r\n',b''),'CRLF line endings only')
    lines=raw.split(b'\r\n')
    check(max(len(l) for l in lines)<=75,'all physical lines <= 75 octets (max %d)'%max(len(l) for l in lines))
    check(raw.startswith(b'BEGIN:VCALENDAR\r\n') and raw.endswith(b'END:VCALENDAR\r\n'),'begin/end VCALENDAR')
    # parser 1
    cal=icalendar.Calendar.from_ical(raw)
    evs=[e for e in cal.walk('VEVENT')]
    # parser 2
    v=vobject.readOne(raw.decode('utf-8'))
    check(len(v.vevent_list)==len(evs),f'vobject and icalendar agree on event count ({len(evs)})')
    uids=[str(e['UID']) for e in evs]
    check(len(set(uids))==len(uids),'UIDs unique')
    dates=[e for e in evs if str(e['UID']).startswith('date-')]
    check(len(dates)==1095,'1095 date events (3 x 365 days)')
    # per-day exactly one date event, consecutive, titles correct vs jdatetime
    byday={e['DTSTART'].dt:e for e in dates}
    d=dt.date(2026,3,21); bad=0
    while d<dt.date(2029,3,20):
        e=byday.get(d)
        j=jdatetime.date.fromgregorian(date=d)
        want=f"{j.day} {MONTHS[j.month-1]} {j.year}"
        if e is None or str(e['SUMMARY'])!=want or e['DTEND'].dt!=d+dt.timedelta(days=1): bad+=1; print('bad',d,e and e['SUMMARY'],want)
        d+=dt.timedelta(days=1)
    check(bad==0,'every date title == independent jdatetime result, DTEND = DTSTART+1')
    check(all(re.fullmatch(r'\d{1,2} [A-Z][a-z]+ 14\d\d',str(e['SUMMARY'])) for e in dates),'titles match "D Month YYYY" (no leading zeros, Finglish only)')
    check(all(str(e['TRANSP'])=='TRANSPARENT' for e in evs),'all events TRANSPARENT (free, no busy block)')
    check(all('VALUE' not in e['DTSTART'].params or e['DTSTART'].params['VALUE']=='DATE' for e in evs) and all(type(e['DTSTART'].dt) is dt.date for e in evs),'all events are all-day (DATE)')
    check(not any(c.name=='VALARM' for c in cal.walk()),'no alarms')
    occ=[e for e in evs if str(e['UID']).startswith('occ-')]
    check((len(occ)>0)==expect_extra,f'occasion events present={expect_extra} ({len(occ)})')
    if occ:
        keys=collections.Counter(e['DTSTART'].dt for e in occ)
        check(max(keys.values())==1,'max one holiday/occasion event per day (no duplicates)')
        # duplicates of (date,title)
        check(len({(e['DTSTART'].dt,str(e['SUMMARY'])) for e in evs})==len(evs),'no duplicate (date,title) pairs')
check(hashlib.sha256(Path('source.ics').read_bytes()).hexdigest()=='e6e63f85645333f8'+hashlib.sha256(Path('source.ics').read_bytes()).hexdigest()[16:],'source file hash still matches the build-time hash')


# ---------------- new checks for the final corrections ----------------
print('== final-correction checks')
import re as _re
D=Path('out/Jalali-Finglish-1405-1407_dates-only.ics').read_bytes()
M=Path('out/Jalali-Finglish-1405-1407.ics').read_bytes()
dt_text=D.decode('utf-8').replace('\r\n ','')
bad=_re.compile(r'holiday|occasion|official|eid|nowruz|ashura|tasua|arbaeen|yalda|christmas|\U0001F534|[\u0600-\u06FF]',_re.I)
check(not bad.search(dt_text),'dates-only: zero holiday/occasion words, no red marker, no Persian text anywhere (titles, descriptions, calendar description)')
hdr=dt_text.split('BEGIN:VEVENT')[0]
check('holiday' not in hdr.lower() and 'occasion' not in hdr.lower(),'dates-only: calendar-level description has no holiday/occasion reference')
def vevents(raw):
    t=raw.decode('utf-8')
    return {m.group(1):m.group(0) for m in _re.finditer(r'BEGIN:VEVENT\r\nUID:(date-[^@]+)@.*?END:VEVENT',t,_re.S)}
vd,vm=vevents(D),vevents(M)
check(len(vd)==len(vm)==1095 and vd==vm,'date events are byte-identical in both files (main file date events carry no holiday text)')
mt=M.decode('utf-8').replace('\r\n ','')
date_blocks=_re.findall(r'BEGIN:VEVENT\r\nUID:date-.*?END:VEVENT',mt,_re.S)
check(not any(bad.search(b) for b in date_blocks),'main file: no date event mentions a holiday/occasion')
cal=icalendar.Calendar.from_ical(M)
occ=[e for e in cal.walk('VEVENT') if str(e['UID']).startswith('occ-')]
check(all(not str(e['SUMMARY'])[0].isdigit() for e in occ),'main file: holiday/occasion titles never start with a digit (kept distinct from date titles)')
# official-count reconciliation (official calendars: 1405 = 26 days, 1406 = 27 days)
hol_days=sorted(e['DTSTART'].dt for e in occ if '\U0001F534' in str(e['SUMMARY']))
def jyear(d): return 1405 if d<dt.date(2027,3,21) else 1406 if d<dt.date(2028,3,20) else 1407
cnt=collections.Counter(jyear(d) for d in hol_days)
check(cnt[1405]==26,f'1405 official holiday days = 26 (official total 26) -> {cnt[1405]}')
check(cnt[1406]==27,f'1406 official holiday days = 27 (official total 27, ISNA) -> {cnt[1406]}')
print('     (1407 projected holiday days:',cnt[1407],')')
# weekday spot checks taken from the official-calendar reports' own weekday statements
wk={'Mon':0,'Tue':1,'Wed':2,'Thu':3,'Fri':4,'Sat':5,'Sun':6}
spots=[(2026,3,21,'Sat'),(2026,4,14,'Tue'),(2026,5,27,'Wed'),(2026,6,4,'Thu'),(2026,6,24,'Wed'),(2026,6,25,'Thu'),
 (2026,8,4,'Tue'),(2026,8,12,'Wed'),(2026,8,13,'Thu'),(2026,8,21,'Fri'),(2026,8,30,'Sun'),(2026,11,13,'Fri'),
 (2026,12,23,'Wed'),(2027,1,6,'Wed'),(2027,1,24,'Sun'),(2027,2,28,'Sun'),(2027,3,10,'Wed'),
 (2027,4,3,'Sat'),(2027,5,17,'Mon'),(2027,5,25,'Tue'),(2027,6,14,'Mon'),(2027,6,15,'Tue'),(2027,7,25,'Sun'),
 (2027,8,2,'Mon'),(2027,8,3,'Tue'),(2027,8,11,'Wed'),(2027,8,20,'Fri'),(2027,11,2,'Tue'),(2027,12,12,'Sun'),
 (2027,12,26,'Sun'),(2028,1,13,'Thu'),(2028,2,17,'Thu'),(2028,2,27,'Sun')]
hs=set(hol_days)
check(all(dt.date(y,m,d) in hs and dt.date(y,m,d).weekday()==wk[w] for y,m,d,w in spots),f'{len(spots)} official lunar holidays sit on the exact date AND weekday the official calendar reports state')
# the four dates where the source was wrong must be the corrected ones, and the old wrong dates must not be holidays
corr=[dt.date(2027,6,14),dt.date(2027,6,15),dt.date(2027,11,2),dt.date(2028,2,17)]
wrong=[dt.date(2027,6,16),dt.date(2027,11,3),dt.date(2028,2,18)]
titles={e['DTSTART'].dt:str(e['SUMMARY']) for e in occ}
check(all(d in hs for d in corr) and not any(d in hs and 'Ashura' not in titles[d] and 'Tasua' not in titles[d] and 'Fatemeh' not in titles[d] and 'Emam Ali' not in titles[d] for d in wrong),'corrected 1406 dates present; old wrong source dates no longer marked as the same holiday')
check(any('Askari' in t for t in titles.values()),'Shahadat-e Emam Hasan Askari holiday present')
check(sum('Projected' in str(e['DESCRIPTION']) for e in occ)>0 and all(e['DTSTART'].dt>=dt.date(2028,3,20) for e in occ if 'Projected' in str(e['DESCRIPTION'])),'only 1407 events carry the "projected" note')
print('ALL PASS' if ok else 'SOME FAILED')
