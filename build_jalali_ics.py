#!/usr/bin/env python3
"""
Build a Finglish Jalali (Persian) calendar for Apple Calendar, 1405-1407.

Source (read-only, never modified):
  https://raw.githubusercontent.com/imanabrisham/Persian-calendar/main/calendar.ics

Output:
  Jalali-Finglish-1405-1407.ics              one "4 Azar 1405" event per day
                                             + one event per holiday/occasion day
  Jalali-Finglish-1405-1407_dates-only.ics   only the "4 Azar 1405" events

Usage:  python3 build_jalali_ics.py source.ics outdir/
"""
import sys, re, hashlib, datetime as dt
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "source.ics")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
OUT.mkdir(parents=True, exist_ok=True)

HOLIDAY_MARK = "\U0001F534"  # red circle in front of official-holiday titles; set "" to remove

MONTHS = ["Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
          "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"]
MONTH_LEN = [31] * 6 + [30] * 5 + [29]
# Weekday names, Python weekday(): Mon=0 ... Sun=6
WEEKDAY_FA = ["Doshanbeh", "Seshanbeh", "Chaharshanbeh", "Panjshanbeh",
              "Jomeh", "Shanbeh", "Yekshanbeh"]

# Nowruz (1 Farvardin) per Jalali year: astronomical vernal equinox, Tehran-noon rule.
NOWRUZ = {1405: dt.date(2026, 3, 21), 1406: dt.date(2027, 3, 21),
          1407: dt.date(2028, 3, 20), 1408: dt.date(2029, 3, 20)}

def to_jalali(d):
    for y in (1405, 1406, 1407):
        if NOWRUZ[y] <= d < NOWRUZ[y + 1]:
            n = (d - NOWRUZ[y]).days
            for m, ln in enumerate(MONTH_LEN, 1):
                if n < ln:
                    return y, m, n + 1
                n -= ln
    raise ValueError(d)

def from_jalali(y, m, day):
    return NOWRUZ[y] + dt.timedelta(days=sum(MONTH_LEN[:m - 1]) + day - 1)

START, END = NOWRUZ[1405], NOWRUZ[1408]          # END exclusive
DAYS = [START + dt.timedelta(days=i) for i in range((END - START).days)]

# ---------------------------------------------------------------- source parsing
def norm(s):
    s = re.sub(r"[\u200c\u200e\u200f\u202a-\u202e\u2066-\u2069]", " ", s)
    s = s.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
    return re.sub(r"\s+", " ", s).strip()

raw = SRC.read_bytes()
src_sha_before = hashlib.sha256(raw).hexdigest()
text = raw.decode("utf-8").replace("\r\n ", "")
FA_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
src_jalali, src_occ = {}, {}
for ev in re.findall(r"BEGIN:VEVENT\r\n(.*?)END:VEVENT", text, re.S):
    ds = re.search(r"DTSTART;VALUE=DATE:(\d{8})", ev).group(1)
    d = dt.date(int(ds[:4]), int(ds[4:6]), int(ds[6:]))
    summ = norm(re.search(r"SUMMARY:(.*)", ev).group(1))
    if "jalali-date-" in ev:
        mname, day = summ.rsplit(" ", 1)
        src_jalali[d] = (FA_MONTHS.index(mname) + 1, int(day))
    else:
        desc = re.search(r"DESCRIPTION:(.*)", ev).group(1)
        src_occ[d] = [norm(p) for p in desc.split("\\n")[1:-1]]

# ---------------------------------------------------------------- mapping check
for d in DAYS:
    y, m, dd = to_jalali(d)
    assert src_jalali[d] == (m, dd), f"mapping mismatch vs source on {d}"
assert len(src_jalali) == len(DAYS) == 1095

# ---------------------------------------------------------------- holidays/occasions
# Fixed Jalali-date official holidays: (month, day) -> (Finglish, Persian)
SOLAR_HOLIDAYS = {
    (1, 1): ("Nowruz (Day 1)", "نوروز"),
    (1, 2): ("Nowruz (Day 2)", "عید نوروز"),
    (1, 3): ("Nowruz (Day 3)", "عید نوروز"),
    (1, 4): ("Nowruz (Day 4)", "عید نوروز"),
    (1, 12): ("Jomhuri-ye Eslami", "روز جمهوری اسلامی"),
    (1, 13): ("Sizdah Bedar", "جشن سیزده به در / روز طبیعت"),
    (3, 14): ("Rehlat-e Emam Khomeini", "رحلت امام خمینی"),
    (3, 15): ("Qiyam-e 15 Khordad", "قیام ۱۵ خرداد"),
    (11, 22): ("Piroozi-ye Enqelab", "پیروزی انقلاب اسلامی"),
    (12, 29): ("Melli Shodan-e Sanat-e Naft", "ملی شدن صنعت نفت ایران"),
}
# Non-holiday occasions on fixed Jalali dates: (month, day) -> (Finglish, Persian, source regex)
SOLAR_OCCASIONS = {
    (2, 1): ("Rooz-e Saadi", "روز بزرگداشت سعدی", r"سعدی"),
    (2, 10): ("Rooz-e Khalij-e Fars", "روز ملی خلیج فارس", r"خلیج فارس"),
    (2, 12): ("Rooz-e Mo'allem", "روز معلم", r"^روز معلم$"),
    (2, 25): ("Rooz-e Ferdowsi", "روز بزرگداشت فردوسی", r"فردوسی"),
    (2, 28): ("Rooz-e Khayyam", "روز بزرگداشت خیام", r"خیام"),
    (4, 13): ("Jashn-e Tirgan", "جشن تیرگان", r"جشن تیرگان"),
    (7, 8): ("Rooz-e Molana", "روز بزرگداشت مولانا", r"مولانا|مولوی"),
    (7, 20): ("Rooz-e Hafez", "روز بزرگداشت حافظ", r"حافظ"),
    (8, 13): ("Rooz-e Daneshamooz", "روز دانش‌آموز", r"دانش آموز"),
    (9, 16): ("Rooz-e Daneshjoo", "روز دانشجو", r"^روز دانشجو$"),
    (9, 30): ("Shab-e Yalda", "شب یلدا", r"یلدا"),
    (11, 10): ("Jashn-e Sadeh", "جشن سده", r"جشن سده"),
}
# Gregorian-date occasions: (month, day) -> (Finglish, Persian)
GREG_OCCASIONS = {
    (1, 1): ("Sal-e No-ye Miladi", "سال نو میلادی"),
    (5, 1): ("Rooz-e Jahani-ye Kargar", "روز جهانی کارگر"),
    (12, 25): ("Christmas", "کریسمس"),
}
# Lunar-calendar holidays. NOT taken from the source file: its lunar dates were checked against
# Iran's official calendar (University of Tehran Geophysics Institute / Public Culture Council,
# as published via ISNA, time.ir and others) and found wrong by one day for several 1406 entries
# and incomplete (Emam Hasan Askari holiday missing).
#   1405, 1406 : OFFICIAL published calendars, entered as Jalali dates.
#   1407       : official calendar not yet published -> PROJECTED Gregorian dates (+/-1 day).
LUNAR_NAMES = {
    "fetr1": ("Eid-e Fetr", "عید سعید فطر"),
    "fetr2": ("Eid-e Fetr (Day 2)", "تعطیل به مناسبت عید سعید فطر"),
    "sadeq": ("Shahadat-e Emam Sadeq", "شهادت امام جعفر صادق (ع)"),
    "qorban": ("Eid-e Qorban", "عید سعید قربان"),
    "ghadir": ("Eid-e Ghadir", "عید سعید غدیر خم"),
    "tasua": ("Tasua", "تاسوعای حسینی"),
    "ashura": ("Ashura", "عاشورای حسینی"),
    "arbaeen": ("Arbaeen", "اربعین حسینی"),
    "rehlat": ("Rehlat-e Payambar & Shahadat-e Emam Hasan", "رحلت پیامبر اکرم و شهادت امام حسن مجتبی"),
    "reza": ("Shahadat-e Emam Reza", "شهادت امام رضا (ع)"),
    "askari": ("Shahadat-e Emam Hasan Askari", "شهادت امام حسن عسکری (ع)"),
    "milad": ("Milad-e Payambar & Emam Sadeq", "میلاد پیامبر اکرم و امام جعفر صادق"),
    "fatemeh": ("Shahadat-e Hazrat-e Fatemeh", "شهادت حضرت فاطمه زهرا (س)"),
    "alibirth": ("Milad-e Emam Ali & Rooz-e Pedar", "ولادت امام علی (ع) و روز پدر"),
    "mabath": ("Mab'ath", "مبعث پیامبر اکرم (ص)"),
    "shaban": ("Nime-ye Sha'ban", "نیمه شعبان، ولادت امام مهدی (عج)"),
    "alimartyr": ("Shahadat-e Emam Ali", "شهادت امام علی (ع)"),
}
OFFICIAL_J = [  # (jalali year, month, day, key)
    (1405, 1, 1, "fetr1"), (1405, 1, 2, "fetr2"), (1405, 1, 25, "sadeq"), (1405, 3, 6, "qorban"),
    (1405, 3, 14, "ghadir"), (1405, 4, 3, "tasua"), (1405, 4, 4, "ashura"), (1405, 5, 13, "arbaeen"),
    (1405, 5, 21, "rehlat"), (1405, 5, 22, "reza"), (1405, 5, 30, "askari"), (1405, 6, 8, "milad"),
    (1405, 8, 22, "fatemeh"), (1405, 10, 2, "alibirth"), (1405, 10, 16, "mabath"),
    (1405, 11, 4, "shaban"), (1405, 12, 9, "alimartyr"), (1405, 12, 19, "fetr1"), (1405, 12, 20, "fetr2"),
    (1406, 1, 14, "sadeq"), (1406, 2, 27, "qorban"), (1406, 3, 4, "ghadir"), (1406, 3, 24, "tasua"),
    (1406, 3, 25, "ashura"), (1406, 5, 3, "arbaeen"), (1406, 5, 11, "rehlat"), (1406, 5, 12, "reza"),
    (1406, 5, 20, "askari"), (1406, 5, 29, "milad"), (1406, 8, 11, "fatemeh"), (1406, 9, 21, "alibirth"),
    (1406, 10, 5, "mabath"), (1406, 10, 23, "shaban"), (1406, 11, 28, "alimartyr"),
    (1406, 12, 8, "fetr1"), (1406, 12, 9, "fetr2"),
]
PROJECTED_G = [  # 1407: (date, key) -- projections, not yet official
    (dt.date(2028, 3, 22), "sadeq"), (dt.date(2028, 5, 6), "qorban"), (dt.date(2028, 5, 14), "ghadir"),
    (dt.date(2028, 6, 3), "tasua"), (dt.date(2028, 6, 4), "ashura"), (dt.date(2028, 7, 14), "arbaeen"),
    (dt.date(2028, 7, 22), "rehlat"), (dt.date(2028, 7, 23), "reza"), (dt.date(2028, 7, 31), "askari"),
    (dt.date(2028, 8, 9), "milad"), (dt.date(2028, 10, 22), "fatemeh"), (dt.date(2028, 12, 1), "alibirth"),
    (dt.date(2028, 12, 15), "mabath"), (dt.date(2029, 1, 1), "shaban"), (dt.date(2029, 2, 6), "alimartyr"),
    (dt.date(2029, 2, 15), "fetr1"), (dt.date(2029, 2, 16), "fetr2"), (dt.date(2029, 3, 11), "sadeq"),
]
PROJ_NOTE = "Projected date: official 1407 calendar not yet published; may shift by 1 day."
# Source-text patterns, used ONLY to report where the source file disagrees with the table above.
SRC_CHECK = {
    "fetr1": r"^عید سعید فطر$", "fetr2": r"^تعطیل( به مناسبت)? عید سعید فطر$", "qorban": r"^عید سعید قربان$",
    "ghadir": r"^عید سعید غدیر خم$", "tasua": r"^تاسوعای حسینی$", "ashura": r"^عاشورای حسینی$",
    "arbaeen": r"^اربعین حسینی$", "rehlat": r"^رحلت.*(پیامبر|رسول) اکرم.*شهادت امام حسن مجتبی",
    "reza": r"^شهادت امام رضا", "milad": r"^میلاد (پیامبر|رسول) اکرم.*امام جعفر صادق",
    "fatemeh": r"^شهادت حضرت فاطمه زهرا", "alibirth": r"^ولادت امام علی (\(ع\)|علیه السلام).*روز پدر",
    "mabath": r"^مبعث", "shaban": r"^ولادت (امام مهدی|حضرت قائم)",
    "alimartyr": r"^شهادت (امام|حضرت) علی (\(ع\)|علیه السلام)$",
    "sadeq": r"^شهادت امام جعفر صادق (\(ع\)|علیه السلام)$", "askari": r"^شهادت امام حسن عسکری",
}

# entries[date] = list of (finglish, persian, is_holiday)
entries = {d: [] for d in DAYS}
def add(d, fin, fa, hol, note=""):
    if d in entries and all(fin != e[0] for e in entries[d]):
        entries[d].append((fin, fa, hol, note))

for d in DAYS:
    y, m, dd = to_jalali(d)
    if (m, dd) in SOLAR_HOLIDAYS:
        add(d, *SOLAR_HOLIDAYS[(m, dd)], True)
    if (m, dd) in SOLAR_OCCASIONS:
        fin, fa, rx = SOLAR_OCCASIONS[(m, dd)]
        add(d, fin, fa, False)
        if not any(re.search(rx, p) for p in src_occ[d]):
            print(f"  note: source has no matching text for {fin} on {d} ({y}/{m}/{dd})")
    if (d.month, d.day) in GREG_OCCASIONS:
        add(d, *GREG_OCCASIONS[(d.month, d.day)], False)

# lunar holidays from the verified table
lunar_dates = {}                                   # key -> [dates]
for jy, jm, jd, key in OFFICIAL_J:
    g = from_jalali(jy, jm, jd)
    lunar_dates.setdefault(key, []).append(g)
    add(g, *LUNAR_NAMES[key], True)
for g, key in PROJECTED_G:
    lunar_dates.setdefault(key, []).append(g)
    add(g, *LUNAR_NAMES[key], True, PROJ_NOTE)

# Mother's/Women's Day = 20 Jumada II = Fatemeh martyrdom (3 Jumada II) + 17 days
for g in lunar_dates["fatemeh"]:
    add(g + dt.timedelta(days=17), "Rooz-e Madar & Zan", "روز مادر و روز زن", False,
        PROJ_NOTE if g >= NOWRUZ[1407] else "")

# Chaharshanbe Suri: the Tuesday evening before the last Wednesday of each Jalali year.
for y in (1405, 1406, 1407):
    last_day = NOWRUZ[y + 1] - dt.timedelta(days=1)
    last_wed = last_day - dt.timedelta(days=(last_day.weekday() - 2) % 7)
    add(last_wed - dt.timedelta(days=1), "Chaharshanbe Suri",
        "جشن چهارشنبه‌سوری (شامگاه سه‌شنبه)", False)

# Report: where does the SOURCE file disagree with the verified table?
print("Source-vs-verified lunar differences (source date -> verified date):")
ndiff = 0
for key, rx in SRC_CHECK.items():
    src_dates = sorted(d for d in DAYS for p in src_occ[d] if re.search(rx, p))
    ver = sorted(lunar_dates.get(key, []))
    for sd in src_dates:
        if sd not in ver:
            near = min(ver, key=lambda v: abs((v - sd).days)) if ver else None
            print(f"  {LUNAR_NAMES[key][0]}: source {sd} -> verified {near}"); ndiff += 1
    for vd in ver:
        if vd not in src_dates and key not in ("askari",):
            if not any(abs((vd - sd).days) == 1 for sd in src_dates if sd not in ver):
                print(f"  {LUNAR_NAMES[key][0]}: verified {vd} absent from source"); ndiff += 1
print("  askari (Emam Hasan Askari): absent/unused in source holiday set -> added from official calendar")

# ---------------------------------------------------------------- ICS writer
def esc(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def fold(line):
    out, cur, cur_len, limit = [], "", 0, 75
    for ch in line:
        b = len(ch.encode("utf-8"))
        if cur_len + b > limit:
            out.append(cur)
            cur, cur_len, limit = " ", 1, 75
        cur += ch
        cur_len += b
    out.append(cur)
    return "\r\n".join(out)

STAMP = "20261125T000000Z"
DOMAIN = "jalali-finglish"

def vevent(uid, d, summary, desc):
    nxt = d + dt.timedelta(days=1)
    lines = ["BEGIN:VEVENT", f"UID:{uid}@{DOMAIN}", f"DTSTAMP:{STAMP}",
             f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{nxt:%Y%m%d}",
             f"SUMMARY:{esc(summary)}", f"DESCRIPTION:{esc(desc)}",
             "SEQUENCE:0", "STATUS:CONFIRMED", "TRANSP:TRANSPARENT", "END:VEVENT"]
    return "\r\n".join(fold(l) for l in lines)

def jtitle(d):
    y, m, dd = to_jalali(d)
    return f"{dd} {MONTHS[m - 1]} {y}"

def date_event(d):
    # Identical in both files and free of any holiday/occasion text.
    desc = f"{WEEKDAY_FA[d.weekday()]} \u2013 {d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"
    return vevent(f"date-{d:%Y%m%d}", d, jtitle(d), desc)

def occ_event(d):
    ev = sorted(entries[d], key=lambda e: not e[2])          # holidays first
    any_hol = any(e[2] for e in ev)
    title = " + ".join(e[0] for e in ev)
    if any_hol and HOLIDAY_MARK:
        title = f"{HOLIDAY_MARK} {title}"
    desc = f"{jtitle(d)} ({WEEKDAY_FA[d.weekday()]})"
    for fin, fa, hol, note in ev:
        desc += f"\n{'Official holiday' if hol else 'Occasion'}: {fin} / {fa}"
        if note:
            desc += f"\n{note}"
    return vevent(f"occ-{d:%Y%m%d}", d, title, desc)

def calendar(name, descr, events):
    head = ["BEGIN:VCALENDAR", "VERSION:2.0",
            "PRODID:-//Jalali Finglish//Persian Calendar 1405-1407//EN",
            "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
            f"X-WR-CALNAME:{esc(name)}", f"X-WR-CALDESC:{esc(descr)}",
            "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:PT24H"]
    body = "\r\n".join(fold(l) for l in head) + "\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR\r\n"
    return body.encode("utf-8")

DATES_DESC = ("Jalali (Persian) date in Finglish, e.g. 4 Azar 1405. Covers 1405-1407. "
              "Date mapping cross-checked against imanabrisham/Persian-calendar.")
FULL_DESC = ("Jalali date in Finglish, e.g. 4 Azar 1405, plus Iranian holidays and occasions as separate "
             "events. Lunar holidays: official calendar for 1405-1406, projected for 1407.")
full = calendar("Jalali Calendar", FULL_DESC,
                [date_event(d) for d in DAYS] + [occ_event(d) for d in DAYS if entries[d]])
dates_only = calendar("Jalali Dates", DATES_DESC, [date_event(d) for d in DAYS])
(OUT / "Jalali-Finglish-1405-1407.ics").write_bytes(full)
(OUT / "Jalali-Finglish-1405-1407_dates-only.ics").write_bytes(dates_only)

assert hashlib.sha256(SRC.read_bytes()).hexdigest() == src_sha_before, "source was modified!"
print("days:", len(DAYS), "| days with holiday/occasion:", sum(1 for d in DAYS if entries[d]),
      "| official-holiday days:", sum(1 for d in DAYS if any(e[2] for e in entries[d])))
print("source sha256 unchanged:", src_sha_before[:16], "...")
