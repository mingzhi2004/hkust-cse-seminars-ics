#!/usr/bin/env python3
"""Build an iCalendar feed from HKUST CSE's public seminar page."""

from __future__ import annotations

import hashlib
import html
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://cse.hkust.edu.hk/pg/seminars/"
OUT = Path(__file__).with_name("cse-seminars.ics")


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line: str) -> str:
    parts = []
    while len(line.encode("utf-8")) > 73:
        cut = 73
        while len(line[:cut].encode("utf-8")) > 73:
            cut -= 1
        parts.append(line[:cut])
        line = " " + line[cut:]
    parts.append(line)
    return "\r\n".join(parts)


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "HKUST-CSE-ICS/1.0"})
    source = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", source, flags=re.I | re.S)
    events = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(cells) < 5:
            continue
        date_text, venue, title, speaker, host = map(clean, cells[:5])
        match = re.search(r"(\d{2} [A-Za-z]{3} 20\d{2}).*?\((\d{2}:\d{2})-(\d{2}:\d{2})\)", date_text)
        if not match or not title or title.lower().startswith("no seminar"):
            continue
        day, start_time, end_time = match.groups()
        start = datetime.strptime(f"{day} {start_time}", "%d %b %Y %H:%M").replace(tzinfo=ZoneInfo("Asia/Hong_Kong"))
        end = datetime.strptime(f"{day} {end_time}", "%d %b %Y %H:%M").replace(tzinfo=ZoneInfo("Asia/Hong_Kong"))
        events.append((start, end, venue, title, speaker, host))

    stamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//mingzhi2004//HKUST CSE Seminars//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:HKUST CSE Seminars",
        "X-WR-TIMEZONE:Asia/Hong_Kong", "X-PUBLISHED-TTL:PT12H",
    ]
    for start, end, venue, title, speaker, host in sorted(events):
        uid = hashlib.sha256(f"{start.isoformat()}|{title}".encode()).hexdigest()[:24] + "@cse.hkust"
        description = f"Speaker: {speaker}\nHost: {host}\nSource: {URL}"
        lines.extend([
            "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=Asia/Hong_Kong:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Asia/Hong_Kong:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{esc('[CSE Seminar] ' + title)}", f"LOCATION:{esc(venue)}",
            f"DESCRIPTION:{esc(description)}", f"URL:{URL}", "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    OUT.write_text("\r\n".join(fold(line) for line in lines) + "\r\n", encoding="utf-8")
    print(f"Wrote {len(events)} events to {OUT}")


if __name__ == "__main__":
    main()
