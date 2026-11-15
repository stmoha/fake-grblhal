# grblHAL Simulator as a copy of a real machine

`fake_grblhal_server.py` (one folder up) pretends to be a controller. This folder is the
other option: the real grblHAL firmware, compiled to run on a PC by the
[grblHAL Simulator](https://github.com/grblHAL/Simulator), built with a real machine's
firmware options and settings. It answers a sender exactly as that machine's controller
would: the same `$$` settings, the same planner and acceleration, rotary A, soft limits,
alarms.

The simulator on its own has no limit switches or probe you can use without pressing
keys in its window, so homing never finishes and probing never touches. `virtual-machine.patch`
fixes that (it only applies when built with `-DVIRTUAL_MACHINE=1`):

- **A physical position for each motor**, counted from the step pulses.
- **Limit switches** on X, Y and Z at the end each axis homes to (`$23`) and just past the
  far end of travel (`$130`–`$132`). The machine starts 20 mm from its switches, so `$H`
  works like on the real thing. Change `$23` and the switches move with it.
- **A probe** that touches 3 mm into any probing move (G38.2–G38.5), so probing, tool
  setters and touch plates can be tested.
- **Inputs read the right way round** whatever the machine's invert settings (`$5`, `$6`,
  `$14` ...), so a machine with normally-closed switches doesn't start in an alarm.
- Hard-limit interrupts are off while homing, as on real drivers.

## Use it

```
grblHAL_sim-stefan-altfinity.exe -n -p 8000
```

Then connect the sender to Ethernet / Telnet, 127.0.0.1, port 8000. Settings are kept in
`EEPROM.DAT` in the folder it runs from: set a value once with `$xxx=...` and it stays.
`-t 2` runs it twice as fast as real time.

## Machines

| File | Machine |
|---|---|
| `machines/stefan-altfinity.flags` | Stefan's Altfinity: Sienci SuperLongBoard32 Ext, 4 axes (A rotary along X). From its firmware's Web Builder `job.ini`: the built-in defaults and the core features. Its board hardware (Ethernet, Modbus spindle, ATCi, RGB lights, SD card, Y auto-squaring) isn't in the simulator. |

The `.flags` file holds the firmware's built-in defaults. A controller remembers settings
changed since it was flashed, so load the machine's own `$$` (ncSender: Settings ›
Firmware › Export) into the simulator once for an exact copy.

To add a machine: take the `-D` lines from its firmware's `job.ini` (Web Builder), keep
`N_AXIS`, the `DEFAULT_...` settings and core features, leave out board hardware.

## Build

```
./build.sh machines/stefan-altfinity.flags            # Linux
./build.sh machines/stefan-altfinity.flags windows    # Windows .exe into bin/ (needs mingw-w64)
python3 test_sim.py PATH/TO/grblHAL_sim               # checks homing, soft limits, probe, A
```

`build.sh` fetches the Simulator at a fixed commit, applies the patch and builds.
`bin/` holds a ready-built Windows `.exe` for each machine.
