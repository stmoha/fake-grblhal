#!/usr/bin/env python3
"""python load_settings.py machines/NAME.settings [--port 8000] [--host 127.0.0.1]

Writes a machine's own $$ settings (one "$n=value" per line, as grblHAL lists them and
ncSender's Settings > Firmware > Export saves them) into a running grblHAL simulator.
The simulator keeps them in its EEPROM.DAT, so this is needed once per simulator folder.

Settings that belong to the real board's add-ons (spindle plugins, ATCi, RGB lights,
networking ...) don't exist in the simulator: grblHAL answers those with an error, and
they're listed at the end so nothing is silently dropped.

Run it while no sender is connected: the simulator serves one connection at a time.
It reads $$ back afterwards to check every accepted value was kept. (grblHAL saves
settings a moment after they change, so this waits before reading back and never resets
straight away, which would lose them.) Restart the simulator for settings that only
apply at start-up to take effect.
"""
import argparse
import re
import socket
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("settings")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    lines = []
    for raw in open(args.settings, encoding="utf-8"):
        line = raw.split("#", 1)[0].strip() if raw.lstrip().startswith("#") else raw.strip()
        if re.match(r"^\$\d+=", line):
            lines.append(line)

    s = socket.create_connection((args.host, args.port), timeout=5)
    s.settimeout(0.05)
    buf = ""

    def reply(timeout=3.0):
        nonlocal buf
        end = time.time() + timeout
        while time.time() < end:
            try:
                buf += s.recv(65536).decode(errors="replace")
            except socket.timeout:
                pass
            for marker in ("ok", "error:"):
                m = re.search(r"^(ok|error:\d+)\s*$", buf, re.M)
                if m:
                    buf = buf[m.end():]
                    return m.group(1)
        return "no answer"

    time.sleep(0.5)
    try:
        buf = s.recv(65536).decode(errors="replace")
    except socket.timeout:
        pass
    buf = ""

    accepted, refused = 0, []
    for line in lines:
        s.sendall((line + "\n").encode())
        r = reply()
        if r == "ok":
            accepted += 1
        else:
            refused.append(f"{line}  ({r})")

    time.sleep(3.0)
    buf = ""
    s.sendall(b"$$\n")
    end, text = time.time() + 5, ""
    while time.time() < end:
        try:
            text += s.recv(65536).decode(errors="replace")
        except socket.timeout:
            if re.search(r"^ok\s*$", text, re.M):
                break
    s.close()
    now = dict(re.findall(r"^\$(\d+)=(.*?)\s*$", text, re.M))
    refused_ids = {r.split("=")[0][1:] for r in refused}

    def same(a, b):
        try:
            return abs(float(a) - float(b)) < 1e-3
        except ValueError:
            return a.strip() == b.strip()

    lost = [l for l in lines if l.split("=")[0][1:] not in refused_ids
            and not same(now.get(l.split("=")[0][1:], "?"), l.split("=", 1)[1])]
    print(f"{accepted} of {len(lines)} settings written to the simulator on {args.host}:{args.port}.")
    if lost:
        print(f"WARNING: {len(lost)} of them don't read back the same: " + ", ".join(lost[:10]))
    else:
        print("Read back with $$: all of them kept.")
    if refused:
        print(f"{len(refused)} not in the simulator (the real board's add-ons):")
        for r in refused:
            print("  " + r)


if __name__ == "__main__":
    main()
