# fake-grblhal

A stand-in grblHAL controller for testing a G-code sender with no machine attached.
It listens on TCP, so a sender connects to it like a networked controller, and it
behaves enough like a real machine that homing, jobs, feed hold and alarms work.

Made for testing [ncSender](https://github.com/siganberg/ncSender) and its plugins (it
was written alongside [Rotary CAM](https://github.com/stmoha/ncsender-plugin-rotary-cam)),
but any sender that talks Grbl over Telnet should work.

One file, Python 3.8 or newer, nothing to install.

## Run it

```
python fake_grblhal_server.py
```

Then in ncSender: Settings › Connection › **Ethernet**, protocol **Telnet**,
IP **127.0.0.1**, port **8000**, and connect.

| Option | What it does |
|---|---|
| `--port 8000` | TCP port to listen on |
| `--axes 4` | `4` = X Y Z + rotary A (degrees), `3` = plain X Y Z |
| `--speed 1` | How much faster than real time moves run: `--speed 10` runs a 20-minute job in 2 |
| `--verbose` | Print everything the sender sends |
| `--host 0.0.0.0` | Address to listen on (use `127.0.0.1` to keep it to this computer) |

Only one sender can be connected at a time. Close the window (or Ctrl+C) to stop it.

## What it does

- **Homing** (`$H`): shows *Home* for a moment, then *Idle* at machine 0. Senders that
  watch for that (ncSender does) count the machine as homed.
- **Jobs take time**: moves go into a 16-move buffer like Grbl's, each takes as long as
  its feed says (mm/min, inches/min, or G93 inverse time; rapids use `$110`–`$113`),
  and the position in the status reports moves along lines and arcs (G2/G3, I J K or R,
  any plane). The status reports the line number being run (`Ln`), which is how
  ncSender shows progress.
- **Feed hold** (`!`), **resume** (`~`), **reset** (Ctrl-X): a reset while moving gives
  *Alarm 3* (`ALARM:3`, and `Alarm:3` in the status, as grblHAL does); `$X` unlocks.
- **Jogging** (`$J=`) and jog cancel.
- **Overrides**: feed, rapid and spindle, shown in `Ov:`.
- **Work offsets**: G54–G59, `G10 L2` / `L20` (the zero buttons), G92, tool length
  offset (G43.1 / G49), reported by `$#`. `$G` reports the modal state, `$$` the
  settings (change them with `$110=3000` and so on).
- **Probing** (G38.2–G38.5): it always touches halfway to the target and reports
  `[PRB:…:1]`.
- **Spindle and coolant** (M3/M4/M5, M7/M8/M9), dwell (G4), M0 pause (resume with `~`),
  M2/M30 program end.
- **A rotary A axis** in degrees (unless `--axes 3`), so 4th-axis jobs and jogs can be
  tested.

## What it doesn't do

It's a test stand-in, not a controller. No acceleration (so jobs run a bit faster than
on a real machine), no soft or hard limits, no checking that the G-code is valid beyond
what a test needs, and nothing is saved when it stops: offsets and settings start fresh
each time.

## Test

```
python test_fake_grblhal.py
```

Starts the fake controller on a spare port and drives it the way a sender does: homing,
offsets, moves and arcs that take the right time, G93, feed hold and resume, overrides,
jog cancel, probing, streaming `examples/rotary-spiral.nc` with the buffer filling up,
and reset into Alarm 3. Pass another `.nc` file to stream that instead. GitHub Actions
runs it on every push.

## License

MIT
