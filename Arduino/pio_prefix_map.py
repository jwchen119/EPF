"""
PlatformIO pre-build script: build with machine-independent source paths.

Assertions and log macros compile source paths in through __FILE__, and with
the framework installed under ~/.platformio those paths depend on the machine
that built the firmware. -ffile-prefix-map makes them start with "~" instead
(it also covers the debug information), so the same source gives the same
strings wherever it is built. The home directory is looked up here, at build
time, because it differs from one machine to the next.
"""
import os

Import("env")  # noqa: F821 - provided by PlatformIO's SCons environment

home = os.path.expanduser("~")
prefixes = {home, home.replace("\\", "/")}
# Some paths come out as "/C:/Users/..." on Windows
prefixes |= {"/" + p for p in prefixes if p[1:3] == ":/"}
for prefix in sorted(prefixes):
    env.Append(CCFLAGS=["-ffile-prefix-map=%s=~" % prefix])  # noqa: F821
