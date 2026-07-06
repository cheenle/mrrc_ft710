#!/usr/bin/env python3
"""
FT-710 Power Cycle via CAT (PS command).
Sends PS0 (off), waits, then sends PS1 (on) to restart the radio.

Usage: python3 _power_cycle.py
"""
import serial
import time
import sys

PORT = "/dev/cu.usbserial-0121DB3A0"  # FT-710 Enhanced COM Port
BAUDRATE = 38400
WAIT_SECONDS = 3  # Time between off and on


def open_port(port: str) -> serial.Serial:
    s = serial.Serial(
        port=port,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1.0,
        write_timeout=1.0,
    )
    time.sleep(0.3)
    s.reset_input_buffer()
    return s


def send_cmd(s: serial.Serial, cmd: str) -> str | None:
    """Send a CAT command and return the response (without trailing ';')."""
    raw = (cmd + ";").encode("ascii")
    s.reset_input_buffer()
    s.write(raw)
    time.sleep(0.3)
    resp = s.read_until(b";")
    if resp:
        return resp.decode("ascii", errors="replace").rstrip(";")
    return None


def power_off(port: str):
    """Send PS0; to turn off the radio."""
    print(f"Opening {port} ...")
    s = open_port(port)
    print("Sending PS0 (power OFF) ...")
    resp = send_cmd(s, "PS0")
    print(f"  Response: {resp}")
    s.close()
    return resp is not None


def power_on(port: str):
    """Send PS1; to turn on the radio. Tries multiple times in case port is
    re-enumerating after power-off."""
    for attempt in range(10):
        try:
            s = open_port(port)
            print("Sending PS1 (power ON) ...")
            resp = send_cmd(s, "PS1")
            print(f"  Response: {resp}")
            s.close()
            if resp is not None and "?" not in (resp or ""):
                return True
            print(f"  Unexpected response, retrying... ({attempt+1}/10)")
            time.sleep(1)
        except Exception as e:
            print(f"  Port not ready ({e}), retrying... ({attempt+1}/10)")
            time.sleep(2)
    return False


def main():
    print("=" * 50)
    print("FT-710 Power Cycle via CAT")
    print("=" * 50)

    # Step 1: Power OFF
    print("\n[1/2] Turning OFF...")
    if not power_off(PORT):
        print("FAILED: Could not send PS0 command.")
        print("Is the radio connected and powered on?")
        sys.exit(1)

    print(f"\nWaiting {WAIT_SECONDS} seconds for radio to power down...")
    time.sleep(WAIT_SECONDS)

    # Step 2: Power ON
    print("\n[2/2] Turning ON...")
    if not power_on(PORT):
        print("FAILED: Could not send PS1 command.")
        print("The radio may need to be turned on manually (press the power button).")
        print("Note: Some FT-710 USB controllers power down completely on PS0.")
        sys.exit(1)

    print("\n✅ Power cycle complete! FT-710 should be back online.")


if __name__ == "__main__":
    main()
