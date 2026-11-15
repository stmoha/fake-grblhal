#!/usr/bin/env python3
"""python3 grblhal-sim/test_sim.py PATH/TO/grblHAL_sim

Checks a virtual-machine build of the grblHAL Simulator: it starts in Alarm when homing is
required, homes on its own virtual switches (Home, then Idle), stops at a soft limit,
probes (G38.2 touches 3 mm in), moves A, and moves the switches when $23 changes.
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

PORT = 18790
fails = 0


def ok(cond, msg):
    global fails
    print(("PASS " if cond else "FAIL ") + msg)
    fails += 0 if cond else 1


class Sim:
    def __init__(self, exe):
        self.dir = tempfile.mkdtemp()
        self.p = subprocess.Popen([exe, "-n", "-p", str(PORT), "-t", "1", "-b", os.devnull, "-s", os.devnull],
                                  cwd=self.dir, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                self.s = socket.create_connection(("127.0.0.1", PORT))
                break
            except OSError:
                time.sleep(0.05)
        self.s.settimeout(0.05)
        self.buf = ""
        self.read(1.0)

    def read(self, t):
        end = time.time() + t
        while time.time() < end:
            try:
                self.buf += self.s.recv(65536).decode(errors="replace")
            except socket.timeout:
                pass
        out, self.buf = self.buf, ""
        return out

    def send(self, line, t=0.5):
        self.s.sendall((line + "\n").encode())
        return self.read(t)

    def status(self):
        self.s.sendall(b"?")
        found = re.findall(r"<[^>]*>", self.read(0.25))
        return found[-1] if found else ""

    def wait_idle(self, t=30):
        end, st = time.time() + t, ""
        while time.time() < end:
            st = self.status()
            if st.startswith("<Idle"):
                break
        return st

    def mpos(self, st):
        return [float(v) for v in re.search(r"MPos:([^|>]*)", st).group(1).split(",")]

    def close(self):
        self.p.kill()


def main():
    exe = os.path.abspath(sys.argv[1])
    sim = Sim(exe)
    try:
        st = sim.status()
        ok(st.startswith("<Alarm"), "starts in Alarm, homing required: " + st)

        sim.s.sendall(b"$H\n")
        seen_home = False
        end = time.time() + 30
        while time.time() < end:
            st = sim.status()
            seen_home |= st.startswith("<Home")
            if st.startswith("<Idle"):
                break
        ok(seen_home and st.startswith("<Idle"), "homes on the virtual switches (Home, then Idle): " + st)
        ok(all(abs(v) < 0.01 for v in sim.mpos(st)[:3]), "homed at machine 0")

        travel_x = 1260
        out = sim.send(f"G21 G90 G53 G0 X{travel_x + 50}", 1.0)
        ok("ALARM:2" in out, "a move past X travel stops at the soft limit (ALARM:2)")
        sim.s.sendall(b"\x18")
        sim.read(1.0)
        sim.send("$H")
        sim.wait_idle(30)

        sim.send("G53 G0 X600 Y-600 Z-60")
        sim.wait_idle()
        out = sim.send("G91 G38.2 Z-30 F200", 3.0)
        st = sim.wait_idle()
        ok("[PRB:" in out and ":1]" in out and abs(sim.mpos(st)[2] - (-63)) < 0.2,
           "G38.2 touches 3 mm into the move and reports [PRB:...:1]: Z " + str(sim.mpos(st)[2]))

        sim.send("G90 G10 L20 P1 X0 Y0 Z0 A0")
        sim.send("G0 A360")
        st = sim.wait_idle()
        ok(abs(sim.mpos(st)[3] - 360) < 0.01, "A turns 360 degrees: " + st)

        sim.send("$23=0")
        sim.s.sendall(b"\x18")
        sim.read(1.0)
        sim.send("$H")
        st = sim.wait_idle(30)
        ok(st.startswith("<Idle") and abs(sim.mpos(st)[0]) < 0.01, "after $23=0 (X homes toward +) it homes again: " + st)
        sim.send("G53 G0 X-600")
        st = sim.wait_idle()
        ok(abs(sim.mpos(st)[0] + 600) < 0.01, "X now runs negative (home at +X)")
    finally:
        sim.close()
    print("\nFAILS:", fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
