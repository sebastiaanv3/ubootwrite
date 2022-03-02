#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple tool to upload data to the RAM of Cisco Meraki MR33 access points
running the U-Boot bootloader.
"""

# This is a modified version of ubootwrite. The original code can be downloaded from github:
# <https://github.com/HorstBaerbel/ubootwrite>
#
# This version of ubootwrite has been modified by ??? to provide support for the U-Boot loader as
# used by the Cisco Meraki MR33 Access Points. The U-Boot command prompt on these APs can
# only be reached if the 'xyzzy' string (CONFIG_AUTOBOOT_STOP_STR) is send during boot.
# This version won't work with regular U-Boot bootloaders, only with Cisco Meraki MR33 APs.

# Cisco Meraki MR33 Access Points are known to have two different versions of bootloaders:
# - "U-Boot 2012.07-g97ab7f1 [local,local] (Oct 06 2016 - 13:07:25)"
#   => Supported.
# - "U-Boot 2017.07-RELEASE-g78ed34f31579 (Sep 29 2017 - 07:43:44 -0700)"
#   => Not supported. No known method exists to enter the U-Boot command prompt, if possible at all.
#
# Please verify which version you have before running this script. Cisco Meraki APs are known
# to auto-update without prior warning.
# You risk permanently bricking your device if you try to enter the U-Boot command prompt on a
# device running any other version then U-Boot 2012.07-g97ab7f1.
# If 'Secure boot NOT enabled! Blowing fuses... Resetting now.' is printed on the serial console,
# it is too late...

# source of modified version:
# https://drive.google.com/drive/folders/1goSM3qgRjna2DFZbhrlLAyfQr4iBwqr_

# Ported from Python2 to Python3 by sebastiaan
# Requires at least Python 3.6
# Tested only using Python 3.9.10 and Python 3.10.2

# Basically it can only be GPLv3, because brntool is.

# Usage
# 0. Connect your computer to the serial port of the Cisco Meraki Access Point.
# 1. Run python3 ubootwrite.py --write=../mr33-uboot.bin --serial=/dev/ttyUSB0
# 2. Power on the Meraki Access Point.

import os
import sys
import time
import struct
import argparse

# If DEBUG is set to True, output is written to a file in the current folder
# and not to the RAM of the device.
DEBUG = False
if not DEBUG:
    import serial

# The maximum size to transfer if we can't determinate the size of the file
# (if input data comes from stdin).
MAX_SIZE = 2 ** 30
LINE_FEED = "\n"


# Wait for the prompt
def getprompt(ser, verbose):
    """Send a command which does not produce a result,
    so when receiving the next line feed
    only the prompt will be returned."""

    # Flushing read buffer
    buf = bytes()
    while True:
        oldbuf = buf
        buf = ser.read(256)
        combined = oldbuf+buf
        if b"machid: 8010001" in combined:
            ser.write("xyzzy".encode())
            while ser.read(256):
                pass
            break

    if verbose:
        print("Waiting for a prompt...")
    while True:
        # Write carriage return and wait for a response
        ser.write(LINE_FEED.encode())
        # Read the response
        buf = ser.read(256)
        if buf.endswith(b"> ") or buf.endswith(b"# "):
            print(f"Prompt is '{buf[2:].decode()}'")
            # The prompt returned starts with a line feed.
            # This is the echo of the line feed we send to get the prompt.
            # We keep this linefeed.
        else:
            # Flush read buffer
            while True:
                buf = ser.read(256)
                if buf.endswith(b"> ") or buf.endswith(b"# "):
                    print(f"Prompt is '{buf[2:].decode()}'")
                    # The prompt returned starts with a line feed.
                    # This is the echo of the line feed we send to get the prompt.
                    # We keep this linefeed.
        return buf


def writecommand(ser, command, prompt, verbose):
    """Wait for the prompt and return True if received or False otherwise"""

    # Write the command and a line feed, we must get back the command and the prompt
    ser.write((command + LINE_FEED).encode())
    buf = ser.read(len(command))
    if buf != command.encode():
        if verbose:
            print(f"Echo command not received. Instead received '{buf.decode()}'.")
        return False

    if verbose:
        print("Waiting for prompt...")

    buf = ser.read(len(prompt))
    if buf == prompt:
        if verbose:
            print("Ok, prompt received.")
        return True
    else:
        if verbose:
            print(f"Prompt '{prompt.decode()}' not received. Instead received '{buf.decode()}'.")
        return False


def memwrite(ser, path, size, start_addr, verbose, shell):
    """Write the contents of the file at `path` to the memory of the device."""

    if not DEBUG and not shell:
        prompt = getprompt(ser, verbose)

    if path == "-":
        fd = sys.stdin
        if size <= 0:
            size = MAX_SIZE
    else:
        fd = open(path,"rb")
        if size <= 0:
            # Get the size of the file
            fd.seek(0, os.SEEK_END)
            size = fd.tell()
            fd.seek(0, os.SEEK_SET)

    addr = start_addr
    bytes_read = 0
    start_time = time.time()
    bytes_last_second = 0
    while bytes_read < size:
        if (size - bytes_read) > 4:
            read_bytes = fd.read(4)
        else:
            read_bytes = fd.read(size - bytes_read)

        # the MR33 mw command needs each 4 byte block reversed
        read_bytes = read_bytes[::-1]

        if len(read_bytes) == 0:
            if path == "-":
                size = bytes_read
            break

        bytes_last_second += len(read_bytes)
        bytes_read += len(read_bytes)

        while len(read_bytes) < 4:
            read_bytes = b'\x00'+read_bytes

        (val, ) = struct.unpack(">L", read_bytes)
        read_bytes = f"{val}"

        str_to_write = f"mw {addr:08x} {val:08x}"
        if verbose:
            print(f"Writing '{str_to_write}' at 0x{addr:08x}")
        if DEBUG:
            str_to_write = struct.pack(">L", int(f"{val:08x}", 16))
        else:
            if not writecommand(ser, str_to_write, prompt, verbose):
                print("Found an error, so aborting.")
                fd.close()
                return False
            # Print progress
            current_time = time.time()
            if (current_time - start_time) > 1:
                percent=(bytes_read * 100) / size
                speed=bytes_last_second / (current_time - start_time) / 1024
                eta=round((size - bytes_read) / bytes_last_second / (current_time - start_time))
                print(f"\rProgress {percent:3.1f}%,  {speed:3.1f}kb/s, ETA {eta:0}s")
                bytes_last_second = 0
                start_time = time.time()

        # Increment address
        addr += 4

    fd.close()

    if bytes_read != size:
        print(f"Error while reading file '{fd.name}' at offset {bytes_read}")
        return False
    else:
        print("\rProgress 100%                            ")
        writecommand(ser, f"bootm {start_addr:08x}", prompt, verbose)
        return True


def upload(ser, path, size, start_addr, verbose, shell):
    """Use the U-Boot command prompt to upload an image to the device memory."""
    while True:
        print("Ready to upload image to device.")
        print("Power on the device now.")
        ret = memwrite(ser, path, size, start_addr, verbose, shell)
        if ret:
            buf = bytes()
            while True:
                oldbuf = buf
                buf = ser.read(256)
                if buf:
                    print(f"COM: {buf.decode()}")

                    combined = oldbuf+buf
                    if b"ERROR: can't get kernel image!" in combined:
                        print("Failed, retry...")
                        break

                    if b"Hello from MR33 U-BOOT" in combined:
                        print("Success!")
                        return


def main():
    """Entry Point"""

    parser = argparse.ArgumentParser("ubootwrite")
    parser.add_argument('--version', action='version', version='%(prog)s 0.2 mr33')
    parser.add_argument("--verbose", action = "store_true",
                        help = "be verbose",
                        dest = "verbose", default = False)
    parser.add_argument("--shell", action = "store_true",
                        help = "I already have a shell, no need to create one for me.",
                        dest = "shell", default = False)
    parser.add_argument("--serial", metavar = "dev",
                        help = "serial port to use",
                        dest = "serial", default = "/dev/ttyUSB0")
    parser.add_argument("--write", metavar = "path",
                        help = "write the contents of a file to the memory of the device",
                        dest = "write")
    parser.add_argument("--uboot", action = "store_true",
                        help = "Only provide access to the Das U-Boot console.",
                        dest = "uboot", default = False)
    parser.add_argument("--addr", metavar = "addr",
                        help = "memory address",
                        dest = "addr", default = "0x82000000")
    parser.add_argument("--size", metavar = "size",
                        help = "# bytes to write",
                        dest = "size", default = "0")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    # Figure out what to do based on the provided command line arguments
    if args.write:
        if DEBUG:
            with open(args.write + ".out", "wb") as ser:
                prompt = getprompt(ser, args.verbose)
                writecommand(ser, "mw 82000000 01234567", prompt, args.verbose)
                buf = ser.read(256)
                print(f"buf = '{buf}'")
        else:
            ser = serial.Serial(args.serial, 115200, timeout=0.1)
            upload(ser, args.write, int(args.size, 0), int(args.addr, 0), args.verbose, args.shell)
    elif args.uboot:
        ser = serial.Serial(args.serial, 115200, timeout=0.1)
        prompt = getprompt(ser, args.verbose)
    else:
        print("No action specified, nothing to do...")


if __name__ == '__main__':
    main()
