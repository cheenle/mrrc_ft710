#!/usr/bin/env python3
"""One-off probe: determine the FT-710's actual SH (WIDTH) command format.

Sends the two candidate SET formats and reads back SH0 after each:
  A) SH00NN  (current code:  SH + P1(0) + P2(0) + 2-digit)
  B) SH0NN   (initial commit: SH + P1(0) + 2-digit)
The radio silently ignores malformed commands, so only the correct
format changes the read-back value. Restores the original width at the end.
"""
import serial
import time

PORT = "/dev/cu.usbserial-0121DB3A0"
BAUD = 38400


def read_resp(ser, prefix, timeout=0.8):
    deadline = time.monotonic() + timeout
    buf = b""
    while time.monotonic() < deadline:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            while b";" in buf:
                frame, buf = buf.split(b";", 1)
                frame = frame.decode("ascii", "replace")
                if frame.startswith(prefix):
                    return frame
        else:
            time.sleep(0.01)
    return None


def send(ser, cmd):
    ser.write((cmd + ";").encode("ascii"))


def query(ser, cmd, prefix=None):
    send(ser, cmd)
    return read_resp(ser, prefix or cmd)


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.3)
    ser.reset_input_buffer()
    send(ser, "AI0")  # stop auto-information stream
    time.sleep(0.2)
    ser.reset_input_buffer()

    print("ID  ->", query(ser, "ID"))
    print("MD0 ->", query(ser, "MD0"))

    orig = query(ser, "SH0")
    print("SH0 original ->", repr(orig))

    send(ser, "SH0013")   # candidate A: SH00NN
    time.sleep(0.3)
    a = query(ser, "SH0")
    print("after 'SH0013;' (SH00NN) ->", repr(a))

    send(ser, "SH017")    # candidate B: SH0NN
    time.sleep(0.3)
    b = query(ser, "SH0")
    print("after 'SH017;'  (SH0NN)  ->", repr(b))

    # restore original width with both formats (whichever the radio accepts)
    if orig and len(orig) >= 2:
        w = orig[-2:]
        send(ser, f"SH00{w}")
        time.sleep(0.2)
        send(ser, f"SH0{w}")
        time.sleep(0.2)
        print("restored ->", repr(query(ser, "SH0")))

    ser.close()


if __name__ == "__main__":
    main()
