# ==============================================================================
# Fish Feeding System - Individual Feeder Pi
# Version: v7.7
# Description: Web interface and control system for individual fish feeder
#              stations running on Raspberry Pi 4
# ==============================================================================
#
# Change LOG:
# V2.0 - started adding in physical control functions
# V2.1 - added manual home button to run the control functions manually
# V2.2 - added more buttons with value inputs on the required functions
# V2.3 - camera fix
# V2.4 - another camera fix
# V2.5 - another camera fix plus added LED function
# V2.6 - global port value tracked
# V2.7/2.8 ??
# V2.9 - adjusted the values to find the food level correctly
# V3.0 - claude attempted to repair the hopper feed and counting opto functions
# V3.1 - manual control page changes
# V3.2 - status on manual control page
# V3.3 - fixed manual control page buttons unresponsive (JS newline escape bug in activity log)
# V3.4 - moved Settle motor button under Load Food, added value input (1-20) passed to SettleMotor
# V3.5 - SettleMotor name conflict resolved (SettleMotorState), home page port fix, camera buffer flush fix, Slack test button
# V4.0 - full code review pass: bug fixes (BlowAirLong GPIO.state, CleanRotor undefined `times`, JiggleRotor int+str concat, broken MQTT initFeeder calls), CheckFoodLevel now actually runs analysis, MovePorts validates start position, exception handling hardened across module-level init / serial / sensor / Slack / threads / main(), API routes refactored with hw_action decorator, _serial_write helper, GPIO.cleanup on exit, sys.excepthook installed, load_webhook reads from sidecar file, home page auto-refreshes, current_port globals consolidated
# V4.1 - removed Microsteps/Turns-per-mg fields from config page, added MICROSTEPS_TO_PORT_ONE constant (replaces hardcoded 4400 in MoveToPortOne), home page heading now shows version
# V4.2 - added Temp Hum log page (Chart.js dual-axis plot), hourly temp/humidity logger to CSV, 5-day rolling retention, pre-seed defaults (22C / 40%) on first boot
# V4.3 - Temp Hum plot now shows last 24 h only (rolling 24 data points); CSV file still stores 5 days for history
# V4.4 - camera preview image scaled to 600x451 in the browser (preserves 1640x1232 aspect ratio); stream resolution unchanged
# V4.5 - added CheckClogs() reading GPIO 4, Check Clog button + Hopper Clogged status row on Manual Control page
# V4.6 - added CheckPower() reading GPIO 17, Check Power button + +24 volts ok status row on Manual Control page
# V4.7 - added CheckAir() reading GPIO 25 (function only, no UI elements)
# V4.8 - added RunFoodSequence() with pre-checks, per-tank feeding loop, post-clean and Slack notifications; skips feeding+clean when no tanks enabled, advances to first enabled tank if port 1 disabled
# V4.9 - RunFoodSequence now Slacks "Food remaining X %" before and after the feeding cycle (forces a fresh food-level read each time)
# V5.0 - added CheckFeedTiming daemon loop; fires RunFoodSequence on a schedule driven by "Feeds per 24 hours"; persists last-feed time across reboots; reads config live so UI changes take effect without restart
# V5.1 - version bump only
# V5.2 - added IdleTubeDry daemon (walks rotor port-by-port between feeds, gated by dry_enabled checkbox), 10-min pre-feed guard, mutual-exclusion lock with RunFoodSequence
# V5.3 - fixed home page "Next Scheduled Feeding" never updating (was hardcoded to "Not scheduled"); added _refresh_next_feeding_time() called from CheckFeedTiming tick and config save handler
# V5.4 - full code review pass: bug fixes (MovePorts off-by-one wrap, RunFoodSequence zero-port-move turning into 60-port spin, IdleTubeDry holding lock during X-min sleep blocking feeds), exception handling hardened (RunFoodSequence per-tank loop now guarantees air solenoid OFF on failure, threading.excepthook installed for daemon thread crashes, Slack send retries once on 5xx, SetupSystemBoot warns when serial port unavailable), concurrency (all hardware API routes acquire _feed_lock via hw_action decorator, MQTT initFeeder lock-wrapped, system_errors bounded at 200 entries), cleanup (dead code removed: WIFI creds, next_port_swap_time, runFoodSchedule stub; immediateFoodNow now actually delegates to RunFoodSequence; display_message renamed to report_crash; food_scale comment fixed; LightTube comment fixed; sidecar directories auto-created; food analysis loop dedupes repeat errors; "Cycle in progress" surfaced on home page; footer summary refreshed; typo "excepion"->"exception")
# V5.5 - fixed home page "Next Scheduled Feeding" sliding (in-memory fallback when last_feed.txt unreadable, removed silent `or datetime.now()` lying); CheckAir polarity corrected (sensor pulls LOW when air flowing — function now returns normalised True/False, all callers updated); current_port concurrency model documented
# V5.6 - inverted the air sensor polarity, it was incorrect
# V5.7 - fixed Immediate Feed silently overwriting the scheduled tank list (was writing form values to TankSettings); RunFoodSequence now takes tank_section parameter, immediateFoodNow writes to ImmediateFeed only
# V5.8 - added activity log textarea to home page (mirrors Manual Control page format), poller now logs "Status refreshed" / failures with timestamps
# V5.9 - home page activity log now shows real backend events (feed cycles, idle dry moves, manual actions, errors) instead of poll noise; new ring buffer + /api/recent_events endpoint, log_event() instrumentation across RunFoodSequence, CheckFeedTiming, IdleTubeDry, immediateFoodNow, hw_action; system_errors_append mirrors errors to the event log
# V6.0 - external port numbering normalised to 1-60 (with "HOME"/"UNKNOWN" labels for special states); new _display_port() helper applied to home page, manual page, /api/status, /api/manual_status and MQTT reqStat; Move ports input range fixed to 1-60 across label/input/JS validator/server validator (was a 3-way mismatch)
# V6.1 - added "Pre-food air dry time" dropdown (5-60s in 5s steps) to Fish Feeder Configuration page; RunFoodSequence now blasts air for the configured duration before each LoadFood to clear moisture from the dispense tube
# V6.2 - added per-tank free-text label input on Fish Feeder Configuration page (40-char max); persisted to TankSettings as tank_<n>_label; pre-populated from saved value on page reload
# V6.3 - RunFoodSequence now Slacks "Feeding tanks: 1,5,6,..." at cycle start and "Next feed scheduled for: <ts>" at cycle end
# V6.4 - per-tank label input moved onto its own row below checkbox/food/mg on Configuration page (was cramped horizontally per attached screenshot); same restructure on Immediate Feed page; new .tank-item-row CSS class
# V6.5 - new "Only dry active tubes" checkbox on Configuration page; when enabled, IdleTubeDry walks only the enabled-tank ports (read fresh from TankSettings on each iteration) instead of every port 1..60; if currently parked on a disabled port, daemon repositions before the next dry wait rather than wasting a cycle
# V6.6 - send Slack notification at startup announcing system online + software version
# V6.7 - food-level calibration overhaul: ROI widened from (120..1340) to (0..1500), vertical extent tightened from 360 px to 180 px (snapshot space) by shifting each y edge inward by 90 snapshot px (y1 500->545, y2 680->635); FOOD_FULL_X = 1446 (right end, where food sits when tube is full), FOOD_EMPTY_X = 0 (left end, where food has receded to when consumed). Earlier in v6.7 these were assigned the wrong way round and a clearly ~60% full tube read 0.76% — the swap brought the reading back in line with reality (~61%)
# V6.8 - revision bump only; v6.7's food-level calibration verified against a known ~60%-full tube (reads ~61%, matches visual estimate)
# V6.9 - food-level percentage rounded to nearest 0.5% via new _round_food_pct() helper applied at all display/notification sites (home page, /api/status, MQTT status, pre/post Slack lines, log_event); RunFoodSequence now Slacks "Food consumed this feeding: X %" at the end of each cycle (pre minus post, clamped to 0 to absorb camera noise; volatile, not persisted)
# V7.0 - RunFoodSequence now also Slacks two derived metrics after each cycle: "% food used per gram" (consumed % divided by total mg dispensed, converted to g) and "No. of feedings left in the feeder" (current remaining % divided by this cycle's consumed %, rounded down). Both volatile, not persisted; computed only when a non-zero consumed delta is available
# V7.1 - RunFoodSequence now collects food_ratio (actual hopper turns / theoretical turns, set by LoadFood) after each per-tank dispense and Slacks the per-cycle mean as "Average hopper food turn ratio" at the end. 1.0 is ideal; lower indicates jamming/slip. Volatile, not persisted.
# V7.2 - scheduling overhauled: legacy "Feeds per 24 hours" interval scheduler replaced with up-to-10 fixed-time daily feed slots set on a new "Feeding times per 24 hour" page (accessed from a button next to Save Configuration / Home Rotor). Strict semantics — a slot whose moment passes while the system is offline is skipped, not caught up. CheckFeedTiming, _minutes_to_next_feed, _refresh_next_feeding_time, post-cycle "Next feed scheduled for" Slack message all rewired to consult _next_scheduled_feed_datetime() instead of the interval math. Legacy feeds_per_24_hours config key left in feeder_config.ini for backwards-compat but no longer consulted.
# V7.3 - UI polish: removed "Home Rotor" button (and its orphaned homeRotor() JS handler) from the bottom of the Configuration page; recoloured the "Temp Hum log" button on the home page from blue/btn-primary to a new dark-mustard btn-temp class so it's visually distinct from the other primary buttons.
# V7.4 - Manual Control page button recolouring: new btn-warning class (orange) for Food Light and Load Food; everything else recoloured per user spec — Home Rotor/Move to Port One/Check food level/Check Clog/Check Power/Slack test/Move ports/Blow Air/Clean Rotor/Settle motor all green (btn-success); Setup allmotion stays grey (btn-secondary).
# V7.5 - removed the never-wired "Regular Feed Schedule" and "Delay Feed by Normal Amount" checkboxes from the Immediate Feed page; cleaned up the matching form reads, config writes, default keys, helper function signature, and the JS handler that gave them mutual-exclusivity behaviour. The .ini keys are no longer written for new configs (existing .inis keep the stale keys harmlessly — they're just orphaned).
# V7.6 - Immediate Feed page now always renders the per-tank label slot (read-only, sourced from TankSettings as before); tanks with no label saved show "N/A" instead of being silently hidden, so the user can see at a glance which tanks have been named.
# V7.7 - home page "Next Scheduled Feeding" tile now uses the same time-on-top / date-below format as the upper clock: 12-hour time with AM/PM rendered bold on the first line, DD:MM (no year) on a smaller line beneath. next_feeding_time now emits the two parts joined with '\n'; home template + JS poller both split on the newline. New .value-sub CSS class added for the date line.


import serial
import os
import io
import time
import board
import adafruit_ahtx0
import RPi.GPIO as GPIO
import datetime
import threading
import configparser
import collections
import cv2
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, Response
import paho.mqtt.client as mqtt

# for slack notifications:
import requests
# for exception crash handling
import sys
import traceback
import atexit
# decorator support for the API hardware-action wrapper
import functools
# imported once at module level (was previously imported inside several camera functions)
from PIL import Image

# ==============================================================================
# CONFIGURATION CONSTANTS
# ==============================================================================

# WiFi configuration is handled at the OS level (wpa_supplicant /
# NetworkManager), not by this script. Removed the unused WIFI_SSID /
# WIFI_PASSWORD constants at v5.4 to avoid a misleading credentials leak.

# MQTT Configuration
MQTT_BROKER_IP = "192.168.1.100"  # PLACEHOLDER: Replace with actual broker IP
MQTT_PORT = 1883
MQTT_QOS = 1
FEEDER_NUMBER = 1  # Hard-coded feeder number (change per Pi: 1-20)
MQTT_COMMAND_TOPIC = f"fishfeeder/feeder{FEEDER_NUMBER}/command"
MQTT_STATUS_TOPIC = f"fishfeeder/feeder{FEEDER_NUMBER}/status"

# Web Server Configuration
WEB_PORT = 8080
HOTEL_NUMBER = FEEDER_NUMBER  # Hotel X matches feeder number

# Configuration File
CONFIG_FILE = "feeder_config.ini"

# Optional sidecar file for the Slack webhook URL. If present and non-empty,
# its contents replace the hard-coded SLACK_WEBHOOK_URL at startup.
# This lets you keep the real webhook out of git without changing source.
SLACK_WEBHOOK_FILE = "/home/fish/Documents/webhook.txt"

# Persisted last-feed timestamp used by CheckFeedTiming() to decide when the
# next scheduled cycle is due. Survives reboots so the feeder picks up where
# it left off rather than firing an immediate feed every time it starts.
LAST_FEED_FILE = "/home/fish/Documents/last_feed.txt"
# Cadence at which CheckFeedTiming wakes up to evaluate whether the
# next-feed time has passed. Independent of the feeding interval itself.
FEED_TIMING_CHECK_INTERVAL = 60   # seconds

# Rolling 5-day temperature/humidity log written by _temp_hum_log_loop().
# Plain CSV: timestamp_iso,temperature_c,humidity_pct
TEMP_HUM_LOG_FILE = "/home/fish/Documents/temp_hum_log.csv"
TEMP_HUM_LOG_INTERVAL = 3600    # one sample per hour
TEMP_HUM_LOG_RETENTION = 120    # keep this many most-recent samples on disk (5 days @ 1/hr)
TEMP_HUM_PLOT_POINTS = 24       # how many of those are shown on the plot page (rolling 24 h)
# Defaults used to pre-seed the log on first startup so the chart isn't empty
# before real samples arrive. Each hourly slot keeps these values until the
# scheduled sample for that slot replaces them with a real reading.
TEMP_HUM_DEFAULT_TEMP = 22.0
TEMP_HUM_DEFAULT_HUM  = 40.0

# Camera Configuration — Pi Camera Module V2.1 (Sony IMX219)
# Full sensor: 3280x2464 (4:3).  Stream uses the same field of view,
# downsampled to exactly half resolution so no part of the image is cropped.
CAMERA_SNAP_WIDTH    = 3280   # Full sensor width  (snapshot)
CAMERA_SNAP_HEIGHT   = 2464   # Full sensor height (snapshot)
CAMERA_STREAM_WIDTH  = 1640   # Half-res width  — same 4:3 FOV (stream)
CAMERA_STREAM_HEIGHT = 1232   # Half-res height — same 4:3 FOV (stream)
CAMERA_FRAMERATE     = 1      # Frames per second for MJPEG stream
# Horizontal crop — pixels to remove from each side edge.
# Applied to both the live stream and snapshots independently
# (i.e. 100 px removed from the stream frame, 100 px from the snapshot frame).
CAMERA_CROP_LEFT  = 500
CAMERA_CROP_RIGHT = 500

# ------------------------------------------------------------------------------
# Food Level Analysis Configuration (migrated from v3.4)
# Calibrate these values to match your physical tube setup.
# These crop values are used ONLY for food analysis (independent of the stream
# crop above). FOOD_ROI coordinates are in the CROPPED image space (i.e. after
# FOOD_CROP_* values have been applied).
# ------------------------------------------------------------------------------
FOOD_CROP_TOP    = 100
FOOD_CROP_BOTTOM = 100
FOOD_CROP_LEFT   = 50
FOOD_CROP_RIGHT  = 50

# Updated for the physical orientation in your snapshot
# Calibrated against the cropped 1540 x 1032 image produced by the
# capture → resize → _apply_crop pipeline. Values measured from an empty-tube
# snapshot: the backlit LED strip spans x ≈ 128..1337 and y ≈ 500..683.
#
# v6.7/v6.8 calibration (verified against a ~60%-full reference snapshot):
#   - ROI widened to span the full LED strip: (0, 545, 1500, 635). Vertical
#     extent is 90 analyser px = 180 snapshot px, tightened from the
#     original 360 snapshot px to exclude top/bottom edge artefacts of the
#     food strip.
#   - Physical model: food sits in the tube and is consumed from the left
#     as the auger pulls it toward the dispense head. The food/empty
#     boundary travels rightward as food depletes. Therefore the FULL
#     anchor is at the RIGHT end of the analysed band (x = 1446) and the
#     EMPTY anchor is at the LEFT end (x = 0). The analyse_food_level
#     function walks inward from the FULL anchor counting dark pixels, so
#     anchor placement matters: a swap was applied during v6.7 testing
#     after a clearly ~60%-full tube briefly read 0.76% with the anchors
#     reversed.
FOOD_ROI     = (0, 545, 1500, 635)    # (x1, y1, x2, y2)
FOOD_FULL_X  = 1446                   # 100% — right end of analysed band (full tube)
FOOD_EMPTY_X = 0                      # 0%   — left end of analysed band (empty tube)
FOOD_THRESHOLD = 180                  # Manual threshold to ensure orange is "dark" vs white
FOOD_ANALYSIS_INTERVAL = 120          # seconds between background analyses

# ==============================================================================
# GLOBAL VARIABLES
# ==============================================================================

# Status variables (volatile)
current_temperature = 0.0
current_humidity = 0.0
food_percentage = 100.0
# Food-loading verification ratio set by LoadFood. Pre-initialised at module
# scope so anything that reads it before the first LoadFood call gets 0.0
# instead of NameError.
food_ratio = 0.0
next_feeding_time = "Not scheduled"
# (next_port_swap_time global was unused — removed at v5.4)
system_errors = []
# Toggle state for the Manual Control "Food Light" button (GPIO 12 via LightTube)
food_light_state = False
# Hardware-tracked rotor port. 99 = unknown, 0..59 = ports 1..60, 100 = HOME.
# Writes to this global happen only inside _feed_lock-protected code paths
# (HomeRotor, MoveToPortOne, MovePorts, SetupSystemBoot). Reads from web
# routes and JS polls happen without the lock — that's safe because Python
# int assignment is atomic under the GIL, so a reader can never see a
# half-written value, only a stale-by-one-step value.
current_port = 99

# MQTT client
mqtt_client = None

# Camera state
camera_lock = threading.Lock()
picam2_instance = None

# Food-level analyser shared state (migrated from v3.4)
_food_analysis_lock        = threading.Lock()
_last_food_analysis_result = {"percentage": None, "timestamp": None, "error": None}

# Mutual-exclusion lock around any code path that drives the rotor / hopper /
# air solenoid via serial. Acquired by RunFoodSequence (full duration),
# IdleTubeDry (only around the actual port move), every /api/... hardware
# route, and the MQTT initFeeder handler. Defined here at the top with the
# other locks so all callers can see it.
_feed_lock = threading.Lock()

# Bound for the system_errors list. Older entries are dropped when this
# threshold is exceeded so a long-running misbehaving sensor can't OOM the
# process by appending forever.
SYSTEM_ERRORS_MAX = 200


# Make sure the sidecar-file directory exists. SLACK_WEBHOOK_FILE,
# LAST_FEED_FILE, and TEMP_HUM_LOG_FILE all live under /home/pi/Documents/
# by default; on a freshly-imaged Pi that directory might not exist, which
# would make every write fail with confusing "permission denied" errors.
# Create it once on startup. Best effort — if this fails, the individual
# read/write attempts will report their own errors.
for _sidecar_path in (SLACK_WEBHOOK_FILE, LAST_FEED_FILE, TEMP_HUM_LOG_FILE):
    try:
        os.makedirs(os.path.dirname(_sidecar_path), exist_ok=True)
    except Exception as _e:
        print(f"[STARTUP] Could not ensure directory for {_sidecar_path}: {_e}")


def system_errors_append(msg):
    """Append to system_errors with a hard cap so a long-running misbehaving
    sensor can't OOM the process by appending forever. Drops oldest entries
    when SYSTEM_ERRORS_MAX is exceeded. Threadsafe (list.append is atomic
    under the GIL; the trim is best-effort).
    """
    system_errors.append(f"{datetime.now().isoformat(timespec='seconds')}: {msg}")
    overflow = len(system_errors) - SYSTEM_ERRORS_MAX
    if overflow > 0:
        del system_errors[:overflow]
    # Mirror error entries to the event log so they show up in the home page
    # activity log along with normal events.
    log_event(f"ERROR: {msg}")


# ==============================================================================
# REAL-TIME EVENT LOG
# ==============================================================================
# Bounded ring buffer of recent backend events, exposed via /api/recent_events
# so the home page can show what the system is doing in near-real-time.
# Each entry: {seq, ts, msg}. seq is monotonic so the JS client can pull only
# what's new since its last poll.
EVENT_LOG_MAX = 200
_event_log = collections.deque(maxlen=EVENT_LOG_MAX)
_event_log_lock = threading.Lock()
_event_log_seq = 0


def log_event(msg):
    """Record a backend event for the home page activity log. Cheap to call;
    safe to call from any thread. Also prints to stdout so terminal-style
    debugging is unchanged.
    """
    global _event_log_seq
    with _event_log_lock:
        _event_log_seq += 1
        entry = {
            "seq": _event_log_seq,
            "ts":  datetime.now().strftime("%H:%M:%S"),
            "msg": str(msg),
        }
        _event_log.append(entry)
    print(f"[EVENT] {entry['ts']} {msg}")


def get_events_since(since_seq):
    """Return a list of event-log entries with seq > since_seq. Used by the
    /api/recent_events endpoint."""
    with _event_log_lock:
        # deque snapshot — copying out under the lock keeps the read consistent.
        return [e for e in _event_log if e["seq"] > since_seq]

# Flask app
app = Flask(__name__)

# UART port: serial driver instance for the AllMotion EZ17 boards.
# Wrapped in try/except so a missing/busy port doesn't kill the process at
# import time — the web UI can still come up to report the failure.
ser = None
try:
    ser = serial.Serial("/dev/serial0", baudrate=9600, timeout=2.0)
    if ser.isOpen():
        print(ser.name + ' is open...')
except Exception as _ser_err:
    print(f"[STARTUP] Serial port unavailable: {_ser_err}")
    system_errors_append(f"Serial init error: {_ser_err}")
    ser = None

# Temp/Hum sensor AHT — same defensive wrap as the serial port.
sensor = None
try:
    sensor = adafruit_ahtx0.AHTx0(board.I2C())
except Exception as _sensor_err:
    print(f"[STARTUP] Temp/Hum sensor unavailable: {_sensor_err}")
    system_errors_append(f"Sensor init error: {_sensor_err}")
    sensor = None

# variable to wait after sending UART command
command_delay = 0.25 # 250milliseconds

# How much food (in milligrams) is dispensed per microstep of the hopper screw.
# 80 mg corresponds to 180° of shaft rotation; at 1/32 microstepping that's
# 3200 microsteps. REV13 used 22.5 µsteps/mg; REV14 added 3:1 gearing so
# the value tripled to 67.5 µsteps/mg. Update if the hopper is rebuilt.
food_scale = 67.5
# Calibrated rotor microstep count for the home → port 1 move.
MICROSTEPS_TO_PORT_ONE = 4400
# Drying time (in minutes) the air-line tube needs after a feeding cycle.
# Live-mirrored from the Configuration page's "Tube dry time (mins):" field
# by load_config()/the form save handler. Used by a function to be defined
# later — referenced here so it has a sensible default if read before the
# config has been loaded.
tube_dry_time = 5
# Live-mirrored from the Configuration page's "Tube dry" checkbox.
# True if the tube-dry step should run as part of a feeding cycle, False to skip it.
dry_enabled = False
# Live-mirrored from the Configuration page's "Only dry active tubes" checkbox.
# When True, IdleTubeDry walks ONLY the enabled tank ports (read from
# TankSettings on each iteration) instead of stepping every port 1..60.
# When False, behaviour is unchanged: every port gets dried in turn.
dry_active_only = False
#food turns counter
glob_food_tn = 0

# The real webhook can be loaded from SLACK_WEBHOOK_FILE at startup; the
# value below is the fallback if that file is missing.
SLACK_WEBHOOK_URL = 'N/A'

# GPIO — explicit setmode call so the file is portable (RPi.GPIO normally
# raises if setmode wasn't called; rpi-lgpio shim tolerates it but the
# explicit call is harmless on both).
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT) # MOSFET 1 LED LIGHT
GPIO.setup(13, GPIO.OUT) # MOSFET 2 VIB MOTOR
GPIO.setup(6, GPIO.OUT) # MOSFET 3 AIR SOLENOID
GPIO.setup(5, GPIO.OUT) # MOSFET 4 SPARE
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # pin to check 24volt power supply
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # pin to check air pressure supply
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # rotor opto signal for HOME
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # hopper screw opto
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # clog sensor

# Hopper screw opto edge counter (polling-thread based).
# At 1.5 rev/s with a 6-slot disc, edges arrive every ~28 ms. The previous
# 50 ms polling aliased; this thread polls at 200 Hz (5 ms) so every transition
# is captured. Runs as a daemon so it dies cleanly when the main process exits.
# (Using a thread instead of GPIO.add_event_detect because that's broken on
# kernel 6.6+ / Bookworm — sysfs interface removed.)
_edge_count = 0
# Lock used to make _edge_count read/reset atomic vs the polling thread's
# load-add-store increment. Without this, a main-thread reset can race with
# an in-flight increment and lose a count.
_edge_count_lock = threading.Lock()


def _opto_polling_thread():
    global _edge_count
    try:
        last_state = GPIO.input(24)
        while True:
            try:
                state = GPIO.input(24)
                if state != last_state:
                    with _edge_count_lock:
                        _edge_count += 1
                    last_state = state
                time.sleep(0.005)  # 5 ms = 200 Hz
            except Exception as inner:
                # Log the error but keep the thread alive — losing edge
                # counting silently would cause LoadFood verification to
                # always read 0 with no clue why.
                print(f"[OPTO] Poll error (continuing): {inner}")
                time.sleep(0.1)
    except Exception as e:
        print(f"[OPTO] Polling thread terminated: {e}")
        system_errors_append(f"Opto polling thread died: {e}")


threading.Thread(target=_opto_polling_thread, daemon=True).start()


# ==============================================================================
# SHARED HELPERS
# ==============================================================================

def _serial_write(command_str):
    """Send a command to the AllMotion driver. Returns True on success.

    Centralised so SerialException, missing port, etc. are handled in one
    place rather than at every call site.
    """
    if ser is None:
        print(f"[SERIAL] Cannot send {command_str!r} — port is not open")
        system_errors_append("Serial write attempted but port is unavailable")
        return False
    try:
        ser.write(command_str.encode())
        return True
    except Exception as e:
        print(f"[SERIAL] Write failed ({command_str!r}): {e}")
        system_errors_append(f"Serial write error: {e}")
        return False


def _gpio_cleanup():
    """Best-effort cleanup of GPIO pins on shutdown so MOSFET-driven loads
    (LED, vibration motor, air solenoid) don't stay energised on crash."""
    try:
        GPIO.output(12, GPIO.LOW)  # LED
        GPIO.output(13, GPIO.LOW)  # vibration motor
        GPIO.output(6, GPIO.LOW)   # air solenoid
        GPIO.output(5, GPIO.LOW)   # spare
    except Exception:
        pass
    try:
        GPIO.cleanup()
    except Exception:
        pass


atexit.register(_gpio_cleanup)

# ==============================================================================
# WEBHOOK AND SLACK ITEMS
# ==============================================================================

def load_webhook():
    """If the optional sidecar file exists, replace SLACK_WEBHOOK_URL with
    its first non-empty line. Failures are non-fatal — we just keep the
    fallback URL and log the reason.
    """
    global SLACK_WEBHOOK_URL
    try:
        if os.path.exists(SLACK_WEBHOOK_FILE):
            with open(SLACK_WEBHOOK_FILE, "r") as f:
                content = f.read().strip()
            if content:
                SLACK_WEBHOOK_URL = content
                print(f"[STARTUP] Slack webhook loaded from {SLACK_WEBHOOK_FILE}")
            else:
                print(f"[STARTUP] {SLACK_WEBHOOK_FILE} exists but is empty; using fallback")
        else:
            print(f"[STARTUP] {SLACK_WEBHOOK_FILE} not present; using fallback webhook")
    except Exception as e:
        print(f"[STARTUP] Could not read {SLACK_WEBHOOK_FILE}: {e}; using fallback")
# end of webhook

def send_slack_notification(message, retries=1):
    """Post a message to Slack. Network failures are caught and logged so
    the caller is never surprised by a hang or an exception bubbling up.
    Retries once on transient failure (network blip, brief 5xx).
    """
    payload = {"text": message}
    last_status = None
    for attempt in range(retries + 1):
        try:
            # 5 s timeout prevents a hang if Slack is unreachable.
            response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        except Exception as e:
            print(f"[SLACK] Network error sending message (attempt {attempt + 1}): {e}")
            if attempt == retries:
                system_errors_append(f"Slack network error: {e}")
                return False
            time.sleep(1)
            continue
        if response.status_code == 200:
            print("✅ Slack message sent successfully!")
            return True
        last_status = response.status_code
        print(f"❌ Failed to send slack message (attempt {attempt + 1}). "
              f"Status code: {response.status_code}")
        # Only retry on transient (5xx) errors; 4xx is a config/permission
        # problem that won't fix itself.
        if response.status_code < 500 or attempt == retries:
            print(f"Response: {response.text}")
            system_errors_append(f"Slack error {response.status_code}: {response.text[:200]}")
            return False
        time.sleep(1)
    return False
# end send slack notification message

# ==============================================================================
# EXCEPTION HANDLING
# ==============================================================================

# Crash notifier — used by the global exception hook below to push a Slack
# message and a console line whenever an unhandled exception kills the main
# thread. Renamed from display_message at v5.4 (the old name suggested a UI
# function); the alias is kept for any external code that may call it.
def report_crash():
    print("⚠ ERROR: Program crashed!")
    # Wrap the Slack send so a crash handler doesn't itself crash if Slack is
    # unreachable (which is likely if the original failure was network-related).
    try:
        send_slack_notification("⚠ ERROR: Program crashed!")
    except Exception as e:
        print(f"[CRASH] Could not send Slack crash notification: {e}")
display_message = report_crash  # backwards-compat alias
# end of crash notifier

# global exception handler:
def global_exception_handler(exc_type, exc_value, exc_traceback):
    # Ignore Ctrl+C so you can stop the program without triggering crash behavior
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
   
    print("Unhandled exception caught:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    report_crash()
    sys.exit(1)
# end of global exception

# Install the global exception handler so unhandled exceptions actually
# trigger report_crash() (which posts to Slack).
sys.excepthook = global_exception_handler

# Daemon threads have their own excepthook (Python 3.8+). Without setting it,
# a thread that raises an unhandled exception dies silently. Hook it to the
# same crash reporter so we get a Slack notification either way.
def _thread_exception_handler(args):
    # args is a threading.ExceptHookArgs namedtuple
    if issubclass(args.exc_type, SystemExit):
        return
    thread_name = args.thread.name if args.thread else '<unknown>'
    print(f"Unhandled exception in thread {thread_name}:")
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
    try:
        send_slack_notification(
            f"⚠ Thread {thread_name} crashed: "
            f"{args.exc_type.__name__}: {args.exc_value}"
        )
    except Exception:
        pass
threading.excepthook = _thread_exception_handler

# ==============================================================================
# CONFIGURATION FILE HANDLING
# ==============================================================================

def load_config():
    """
    Loads configuration from INI file.
   
    Inputs: None
    Outputs: configparser.ConfigParser object with loaded settings
    """
    print("[CONFIG] Loading configuration from file...")
    config = configparser.ConfigParser()
   
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        print("[CONFIG] Configuration loaded successfully")
    else:
        print("[CONFIG] No configuration file found, creating defaults")
        config = create_default_config()
        save_config(config)

    # Mirror the tube_dry_time setting into the module-level variable.
    try:
        global tube_dry_time
        tube_dry_time = config.getint('FeedSchedule', 'tube_dry_time', fallback=5)
    except Exception as e:
        print(f"[CONFIG] Could not mirror tube_dry_time: {e}")

    # Mirror the dry_enabled checkbox.
    try:
        global dry_enabled
        dry_enabled = config.getboolean('FeedSchedule', 'dry_enabled', fallback=False)
    except Exception as e:
        print(f"[CONFIG] Could not mirror dry_enabled: {e}")

    # Mirror the dry_active_only checkbox.
    try:
        global dry_active_only
        dry_active_only = config.getboolean('FeedSchedule', 'dry_active_only', fallback=False)
    except Exception as e:
        print(f"[CONFIG] Could not mirror dry_active_only: {e}")

    return config


def create_default_config():
    """
    Creates default configuration settings.
   
    Inputs: None
    Outputs: configparser.ConfigParser object with default settings
    """
    print("[CONFIG] Creating default configuration...")
    config = configparser.ConfigParser()
   
    # Tank settings section
    config['TankSettings'] = {}
    for i in range(1, 61):
        config['TankSettings'][f'tank_{i}_enabled'] = 'false'
        config['TankSettings'][f'tank_{i}_food_mg'] = '50'
        config['TankSettings'][f'tank_{i}_label']   = ''
   
    # Feed schedule settings
    # Note (v7.2): the legacy 'feeds_per_24_hours' key is retained in the
    # config for safety (so an older config file still parses) but is no
    # longer read by the scheduler — see feed_N_enabled / feed_N_time below.
    config['FeedSchedule'] = {
        'feeds_per_24_hours': '2',
        'rotor_wiggle_enabled': 'false',
        'wiggle_number': '0',
        'main_air_pulse_time': '5',
        'wiggle_air_pulse_time': '1.0',
        'pre_food_air_dry_time': '5',
        'tube_dry_time': '5',
        'dry_enabled': 'false',
        'dry_active_only': 'false',
        'microsteps_to_port1': '1000',
        'turns_per_mg_food': '0.5'
    }
    # 10 explicit per-day feed slots (v7.2). All disabled by default — the
    # user enables and times the ones they want via the new "Feeding times
    # per 24 hour" page. Pre-populated defaults (useful intervals for the
    # first 6, 00:00 for the rest) so the dropdowns show sensible starting
    # times even before the user touches them.
    _default_times = [
        '06:00', '09:00', '12:00', '15:00', '18:00', '21:00',
        '00:00', '00:00', '00:00', '00:00',
    ]
    for i in range(1, 11):
        config['FeedSchedule'][f'feed_{i}_enabled'] = 'false'
        config['FeedSchedule'][f'feed_{i}_time']    = _default_times[i-1]
   
    # Immediate feed settings
    config['ImmediateFeed'] = {}
    for i in range(1, 61):
        config['ImmediateFeed'][f'tank_{i}_enabled'] = 'false'
        config['ImmediateFeed'][f'tank_{i}_food_mg'] = '50'

    # v7.5: removed the never-implemented 'regular_schedule' and 'delay_feed'
    # keys. They were stored and round-tripped through the form but no code
    # path consulted them; the corresponding checkboxes have been removed
    # from the Immediate Feed page.

    print("[CONFIG] Default configuration created")
    return config


def save_config(config):
    """
    Saves configuration to INI file.
   
    Inputs: config - configparser.ConfigParser object
    Outputs: None (writes to file)
    """
    print("[CONFIG] Saving configuration to file...")
    try:
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        print("[CONFIG] Configuration saved successfully")
    except Exception as e:
        print(f"[CONFIG] Error saving configuration: {e}")
        system_errors_append(f"Config save error: {e}")


# ==============================================================================
# HARDWARE FUNCTIONS (PLACEHOLDERS)
# ==============================================================================

# Read the air-pressure sensor on GPIO 25 and return True if pressure is
# present, False if not. The pressure switch on this build is wired such
# that it pulls the GPIO LOW when air is flowing — so we have to invert
# the raw pin reading. If a future hardware revision flips the polarity,
# change AIR_SENSE_PRESENT to GPIO.HIGH and nothing else.
AIR_SENSE_PRESENT = GPIO.LOW

def CheckAir():
    """Return True if air pressure is present at the sensor, False otherwise.
    All callers should compare against True/False (or use the value directly
    in a boolean context); they should NOT compare against GPIO.HIGH/LOW.
    """
    print("[HARDWARE] Checking the air pressure monitor")
    raw = GPIO.input(25)
    pressure_present = (raw == AIR_SENSE_PRESENT)
    print(f"[HARDWARE] Air pressure monitor: raw={'HIGH' if raw else 'LOW'} "
          f"-> {'PRESSURE PRESENT' if pressure_present else 'NO PRESSURE'}")
    return pressure_present
# end of air check

# Read the +24 V power monitor pin (GPIO 17). Returns GPIO.HIGH or GPIO.LOW.
# HIGH means +24 V is present; LOW means the supply has failed.
def CheckPower():
    print("[HARDWARE] Checking the +24 V power monitor")
    state = GPIO.input(17)
    print(f"[HARDWARE] +24 V monitor: {'HIGH (OK)' if state else 'LOW (failed)'}")
    return state
# end of power check

# Read the clog-sensor pin (GPIO 4). Returns GPIO.HIGH or GPIO.LOW directly.
# HIGH means the hopper is clogged; LOW means no clog.
def CheckClogs():
    print("[HARDWARE] Checking the hopper clog sensor")
    state = GPIO.input(4)
    print(f"[HARDWARE] Clog sensor state: {'HIGH (clogged)' if state else 'LOW (no clog)'}")
    return state
# end of clog check

def _ports_forward(current_zero_idx, target_one_idx):
    """Compute the number of forward ports needed to move from a 0-indexed
    current port to a 1-indexed target port, wrapping at 60. Returns 0
    when already at the target (caller can skip the move). Used by
    RunFoodSequence to walk between enabled tanks unambiguously.
    """
    target_zero_idx = target_one_idx - 1
    diff = target_zero_idx - current_zero_idx
    if diff < 0:
        diff += 60
    return diff


def _display_port(internal_port):
    """Convert the internal current_port value (0..59 = ports 1..60,
    99 = unknown, 100 = HOME) into a user-facing string. All web pages
    and API responses go through this so the user never sees the raw
    0-indexed value (which is confusing — port 1 displaying as "0").
    """
    if internal_port == 100:
        return "HOME"
    if internal_port == 99:
        return "UNKNOWN"
    if 0 <= internal_port <= 59:
        return str(internal_port + 1)
    # Out-of-range — surface it rather than hide it; helps debugging.
    return f"INVALID({internal_port})"


def _round_food_pct(pct):
    """Round a food-level percentage to the nearest 0.5%. Used at every
    display/notification site so the home page, API responses, MQTT status
    and Slack messages all show the same friendly granularity rather than
    a noisy float like 78.4127%. Internal storage of food_percentage stays
    full-precision; this is purely a presentation rounding.
    """
    try:
        return round(float(pct) * 2) / 2
    except (TypeError, ValueError):
        return pct


# ------------------------------------------------------------------------------
# Top-level feeding sequence — strings together the lower-level hardware
# functions in the order required for a scheduled or immediate feed run.
# Returns True on full successful completion, False if the pre-checks fail
# and the sequence is halted.
#
# `tank_section` selects which config section provides the per-tank enable
# flags and food amounts:
#   - 'TankSettings' (default): values from the Fish Feeder Configuration
#     page; used by scheduled feeds.
#   - 'ImmediateFeed': values from the Immediate Feed page; used when the
#     user clicks the on-demand feed button.
# Both sections use the same key naming (tank_<n>_enabled, tank_<n>_food_mg)
# so the rest of the function reads them generically.
# ------------------------------------------------------------------------------
def RunFoodSequence(tank_section='TankSettings'):
    print(f"[SEQUENCE] === Starting RunFoodSequence (section={tank_section}) ===")
    log_event(f"Feed cycle starting (section={tank_section})")

    # ---- ONE-SHOT PRE-CHECKS ------------------------------------------------
    clog_state  = CheckClogs()
    power_state = CheckPower()
    air_state   = CheckAir()
    HomeRotor()
    MoveToPortOne()

    # Pre-check pass conditions: clog LOW (no clog), power HIGH (24 V good),
    # air NOT pressurised (no air commanded yet so the sensor should be
    # reading "no pressure"), and the rotor at port 1 (current_port == 0
    # in the 0..59 numbering).
    pre_check_ok = (clog_state == GPIO.LOW
                    and power_state == GPIO.HIGH
                    and air_state is False     # CheckAir returns True/False; False = no pressure
                    and current_port == 0)

    # Track the pre-cycle food level so we can Slack the consumed amount
    # at the end. Volatile — never persisted to disk; recomputed every cycle.
    food_pct_at_start = None

    if pre_check_ok:
        send_slack_notification("Feeding cycle pre-check sequence no exceptions found")
        log_event("Pre-checks OK")
        # Take a fresh food-level reading and Slack it before the cycle starts.
        try:
            _run_food_analysis_from_camera()
        except Exception as e:
            print(f"[SEQUENCE] Food-level read failed before cycle: {e}")
        food_pct_at_start = food_percentage
        send_slack_notification(f"Food remaining {_round_food_pct(food_percentage)} %")
        log_event(f"Food remaining {_round_food_pct(food_percentage)}%")
    else:
        send_slack_notification("Feeding cycle pre-check exception found, halting")
        log_event("Pre-check FAILED — halting")

    # ---- AIR-PRESSURE SELF-TEST --------------------------------------------
    BlowAirLong(GPIO.HIGH)            # turn the air on
    time.sleep(0.5)
    air_with_pressure = CheckAir()    # should now return True (pressure present)
    BlowAirLong(GPIO.LOW)             # turn the air off

    if air_with_pressure:
        send_slack_notification("Pre-check air pressure good")
        air_test_ok = True
    else:
        send_slack_notification("Pre-check air pressure failed, halting")
        air_test_ok = False

    # ---- HALT IF EITHER PRE-CHECK FAILED -----------------------------------
    if not pre_check_ok or not air_test_ok:
        diagnostic = (
            f"Feeding sequence halted. Sensors: "
            f"clog={'HIGH' if clog_state else 'LOW'}, "
            f"power={'HIGH' if power_state else 'LOW'}, "
            f"air_idle={'PRESSURE' if air_state else 'NO PRESSURE'}, "
            f"air_with_pressure={'PRESSURE' if air_with_pressure else 'NO PRESSURE'}, "
            f"current_port={current_port}"
        )
        send_slack_notification(diagnostic)
        print(f"[SEQUENCE] {diagnostic}")
        return False

    # ---- SETTLE FOOD BEFORE DISPENSING -------------------------------------
    SettleMotor(3)  # 3 second vibrate

    # ---- LOAD FRESH CONFIG -------------------------------------------------
    # Re-read from disk every cycle so edits saved through the Configuration
    # web page take effect on the next feeding.
    try:
        cfg = load_config()
    except Exception as e:
        print(f"[SEQUENCE] Could not load config (aborting): {e}")
        send_slack_notification(f"Feeding cycle aborted — config load failed: {e}")
        return False

    # ---- BUILD ENABLED-TANK LIST FROM CONFIG -------------------------------
    # Tanks are 1..60. current_port uses 0..59. We collect the enabled
    # tanks in numeric order along with their food amount (mg). The
    # tank_section argument selects scheduled (TankSettings) vs immediate
    # (ImmediateFeed) — both sections use identical key naming.
    enabled_tanks = []
    for i in range(1, 61):
        try:
            if cfg.getboolean(tank_section, f'tank_{i}_enabled', fallback=False):
                amount_mg = cfg.getint(tank_section, f'tank_{i}_food_mg', fallback=50)
                enabled_tanks.append((i, amount_mg))
        except Exception as e:
            print(f"[SEQUENCE] Could not read tank {i} from {tank_section}: {e}")

    print(f"[SEQUENCE] Enabled tanks for this cycle ({tank_section}): {enabled_tanks}")

    # ---- EARLY RETURN IF NO TANKS ENABLED ----------------------------------
    # No point spinning the rotor and burning a clean cycle for nothing.
    if not enabled_tanks:
        send_slack_notification("Feeding cycle skipped — no tanks enabled in configuration")
        log_event("Feed cycle skipped — no tanks enabled")
        print("[SEQUENCE] No enabled tanks; skipping feed + clean.")
        return True

    # Slack the list of tanks that are about to be fed so an operator
    # watching the channel knows what this cycle is going to do.
    enabled_tank_numbers = ",".join(str(t[0]) for t in enabled_tanks)
    send_slack_notification(f"Feeding tanks: {enabled_tank_numbers}")
    log_event(f"Feeding tanks: {enabled_tank_numbers}")

    # ---- READ SCHEDULE-WIDE PARAMETERS FROM CONFIG -------------------------
    try:
        wiggle_enabled       = cfg.getboolean('FeedSchedule', 'rotor_wiggle_enabled', fallback=False)
        wiggle_count         = cfg.getint('FeedSchedule', 'wiggle_number', fallback=0)
        main_air_pulse_time  = cfg.getint('FeedSchedule', 'main_air_pulse_time', fallback=5)
        pre_food_air_dry_time = cfg.getint('FeedSchedule', 'pre_food_air_dry_time', fallback=5)
    except Exception as e:
        print(f"[SEQUENCE] Could not read FeedSchedule keys: {e}")
        wiggle_enabled, wiggle_count, main_air_pulse_time = False, 0, 5
        pre_food_air_dry_time = 5

    # ---- ADVANCE TO FIRST ENABLED TANK (IF NOT PORT 1) ---------------------
    # MoveToPortOne earlier left us at current_port == 0 (i.e. port 1).
    # If tank 1 is disabled, step forward to whichever enabled tank is first.
    first_tank_number = enabled_tanks[0][0]
    if first_tank_number != 1:
        ports_to_skip = _ports_forward(current_port, first_tank_number)
        if ports_to_skip > 0:
            print(f"[SEQUENCE] Tank 1 disabled; advancing {ports_to_skip} ports to tank {first_tank_number}")
            MovePorts(ports_to_skip)

    # ---- PER-TANK FEEDING LOOP ---------------------------------------------
    # Wrap the entire loop in try/except/finally so that if any single step
    # raises (LoadFood serial timeout, JiggleRotor failure, etc.) we still
    # de-energise the air solenoid before propagating. Without this, a crash
    # mid-loop could leave the solenoid latched ON until the next feed cycle
    # or program restart.
    cycle_succeeded = True
    # Per-cycle hopper food-turn ratios. food_ratio (module global) is the
    # ratio of actual opto-counted screw turns to theoretical turns,
    # recomputed by LoadFood after every dispense — ideally 1.0; values
    # below 1.0 indicate the motor jammed/skipped. We collect each tank's
    # value here so we can Slack the per-cycle average at the end.
    # Volatile — never persisted to disk; reset on every RunFoodSequence call.
    cycle_food_ratios = []
    try:
        for index, (tank_number, amount_mg) in enumerate(enabled_tanks):
            print(f"[SEQUENCE] --- Tank {tank_number} ({amount_mg} mg) ---")
            log_event(f"Feeding tank {tank_number} ({amount_mg} mg)")

            # 1. Pre-food air dry blast (clears moisture from the dispense
            # tube before the food motor turns). Duration set on the Fish
            # Feeder Configuration page as "Pre-food air dry time".
            BlowAir(pre_food_air_dry_time)

            # 2. Dispense food
            LoadFood(amount_mg)
            # LoadFood updates the module global food_ratio as a side
            # effect. Snapshot it now (defensive copy — the global will be
            # overwritten by the next tank's LoadFood). Skip zero/None
            # values, which indicate LoadFood early-returned (e.g. amount_mg
            # was 0) and didn't actually run the motor.
            try:
                if food_ratio:
                    cycle_food_ratios.append(float(food_ratio))
            except Exception:
                pass

            # 3. Air on
            BlowAirLong(GPIO.HIGH)

            # 4. Small settle delay
            time.sleep(0.5)

            # 5. Verify air pressure is present (logged for diagnostics)
            air_during_pulse = CheckAir()
            if not air_during_pulse:
                print(f"[SEQUENCE] WARNING: air sensor reports no pressure during pulse for tank {tank_number}")

            # 6. Hold the air pulse for the configured duration
            time.sleep(main_air_pulse_time)

            # 7. Air off
            BlowAirLong(GPIO.LOW)

            # 8. Optional rotor wiggle
            if wiggle_enabled and wiggle_count > 0:
                JiggleRotor(wiggle_count, 200)  # intensity hardcoded for now

            # 9. 1-second air blast
            BlowAir(1)  # duration hardcoded for now

            # 10. Move to the next enabled tank (skipping the move after the last)
            if index < len(enabled_tanks) - 1:
                next_tank_number = enabled_tanks[index + 1][0]
                ports_to_move = _ports_forward(current_port, next_tank_number)
                # Skip a zero-port move (e.g. duplicate tank in config).
                # The previous code turned this into a full 60-port revolution.
                if ports_to_move > 0:
                    MovePorts(ports_to_move)
    except Exception as loop_err:
        cycle_succeeded = False
        print(f"[SEQUENCE] Per-tank loop crashed: {loop_err}")
        traceback.print_exc()
        system_errors_append(f"RunFoodSequence loop error: {loop_err}")
        send_slack_notification(f"Feeding cycle aborted mid-loop: {loop_err}")
    finally:
        # Always make sure the air solenoid is off at the end of the loop,
        # regardless of which path we took out.
        try:
            BlowAirLong(GPIO.LOW)
        except Exception:
            pass

    if not cycle_succeeded:
        return False

    # ---- POST-CYCLE CLEAN ---------------------------------------------------
    # NOTE: clean_cycles is currently hardcoded to 2. The Manual Control page's
    # Clean Rotor input is not persisted — when (later) you want this configurable,
    # add a 'clean_rotor_cycles' key to the FeedSchedule config and read it here.
    CleanRotor(2)

    send_slack_notification("Feeding cycle and rotor cleaning completed no exceptions found")
    log_event("Feed cycle complete, rotor cleaning done")
    # Take a fresh food-level reading and Slack it after the cycle completes.
    try:
        _run_food_analysis_from_camera()
    except Exception as e:
        print(f"[SEQUENCE] Food-level read failed after cycle: {e}")
    send_slack_notification(f"Food remaining {_round_food_pct(food_percentage)} %")
    log_event(f"Food remaining {_round_food_pct(food_percentage)}% (post-cycle)")

    # Slack how much food this cycle consumed — pre minus post, clamped to
    # zero so that camera noise pushing the post reading slightly above the
    # pre reading doesn't display as a negative consumption. Volatile;
    # never persisted to disk. Skipped silently if no pre-cycle reading
    # was taken (e.g. pre-check failed before the food camera fired).
    if food_pct_at_start is not None:
        try:
            consumed = max(0.0, float(food_pct_at_start) - float(food_percentage))
            send_slack_notification(f"Food consumed this feeding: {_round_food_pct(consumed)} %")
            log_event(f"Food consumed this feeding: {_round_food_pct(consumed)}%")

            # Derived metrics — volatile, computed inline, not persisted.
            # Total food dispensed this cycle in grams: sum of the per-tank
            # mg values (enabled_tanks was built above; each entry is
            # (tank_number, amount_mg)). Skip silently if anything looks
            # off (no enabled tanks, can't sum, etc.).
            total_grams = sum(amt for _, amt in enabled_tanks) / 1000.0

            # "% food used per gram" — the cycle's consumed percentage
            # divided by the grams dispensed. Guarded against a zero
            # divisor (which shouldn't happen because the no-tanks case
            # returns early, but defensive code is cheap).
            if total_grams > 0:
                pct_per_gram = consumed / total_grams
                send_slack_notification(
                    f"% food used per gram: {_round_food_pct(pct_per_gram)} %"
                )
                log_event(f"% food used per gram: {_round_food_pct(pct_per_gram)}%")

                # "No. of feedings left in the feeder" — current remaining
                # % divided by this cycle's consumed %. Rounded down via
                # int() so we never overstate how many feedings remain.
                # Guarded against a zero consumed (would be infinite).
                if consumed > 0:
                    feedings_left = int(float(food_percentage) / consumed)
                    send_slack_notification(
                        f"No. of feedings left in the feeder: {feedings_left}"
                    )
                    log_event(f"No. of feedings left in the feeder: {feedings_left}")
        except Exception as e:
            print(f"[SEQUENCE] Could not compute consumed-food delta: {e}")

    # Average hopper food turn ratio for this cycle — the mean of each
    # tank's food_ratio (actual screw turns / theoretical turns). 1.0 is
    # ideal; lower indicates the hopper screw is jamming or slipping on
    # one or more tanks. Volatile; never persisted. Only sent if at least
    # one tank actually ran the hopper motor.
    try:
        if cycle_food_ratios:
            avg_ratio = sum(cycle_food_ratios) / len(cycle_food_ratios)
            send_slack_notification(
                f"Average hopper food turn ratio: {round(avg_ratio, 2)}"
            )
            log_event(f"Average hopper food turn ratio: {round(avg_ratio, 2)}")
    except Exception as e:
        print(f"[SEQUENCE] Could not compute average hopper food turn ratio: {e}")

    # Compute and Slack the next-scheduled-feed time so an operator can see
    # at a glance when the feeder will fire next. v7.2: uses the new
    # fixed-time slot scheduler — returns None when no slots are enabled,
    # in which case we explicitly say "not scheduled" rather than make
    # up a time.
    try:
        nxt = _next_scheduled_feed_datetime()
        if nxt is not None:
            next_at = nxt.strftime("%Y-%m-%d %H:%M:%S")
            send_slack_notification(f"Next feed scheduled for: {next_at}")
            log_event(f"Next feed scheduled for: {next_at}")
        else:
            send_slack_notification("Next feed scheduled for: not scheduled (no slots enabled)")
            log_event("Next feed scheduled for: not scheduled")
    except Exception as e:
        print(f"[SEQUENCE] Could not compute next-feed time: {e}")

    print("[SEQUENCE] === RunFoodSequence complete ===")
    return True
# end of RunFoodSequence


# ------------------------------------------------------------------------------
# CheckFeedTiming — daemon loop that decides when the next scheduled feeding
# cycle is due, then runs RunFoodSequence() and waits for the next slot.
#
# Behavior (v7.2 onwards — fixed-time scheduling):
#   - Reads 10 explicit "feed_N_enabled / feed_N_time" slots from
#     [FeedSchedule] in feeder_config.ini on every tick. Each slot has a
#     HH:MM local-clock time. The user sets these on the "Feeding times
#     per 24 hour" page.
#   - On each tick, computes today's local datetime for every enabled slot
#     and fires any slot whose firing moment was crossed since the last
#     tick. STRICT semantics: if the system was offline / busy when a slot
#     passed, that slot is SKIPPED (no catch-up); the operator can issue
#     a manual feed if needed.
#   - Tracks which slot last fired on which calendar day so the same slot
#     can't fire twice in one day, and re-arms automatically at midnight.
#   - 0 enabled slots -> automatic feeding is disabled. The loop keeps
#     polling so re-enabling via the web UI takes effect without restart.
#
# The legacy interval-based scheduler (driven by "Feeds per 24 hours")
# was removed at v7.2. The old config key is left in feeder_config.ini
# for backwards-compat but no longer consulted by any code path.
# ------------------------------------------------------------------------------

# In-memory fallback for the last-feed timestamp. Used when LAST_FEED_FILE
# can't be read or written (missing directory, permissions issue, full disk).
# Without this fallback, every call to _read_last_feed_time() would return
# None, the home page's "Next Scheduled Feeding" would slide forward in real
# time on every refresh, and scheduled feeds would never fire (because
# elapsed would always be ~0).
# Process-local; lost on restart, which is fine: a restart will re-anchor
# to "now" via CheckFeedTiming's startup block.
_last_feed_fallback = None
_last_feed_fallback_lock = threading.Lock()


def _read_last_feed_time():
    """Return the persisted last-feed time as a datetime, or None if both
    the on-disk file and the in-memory fallback are unavailable.
    """
    if os.path.exists(LAST_FEED_FILE):
        try:
            with open(LAST_FEED_FILE, "r") as f:
                text = f.read().strip()
            if text:
                return datetime.fromisoformat(text)
        except Exception as e:
            print(f"[FEED_TIMING] Could not parse {LAST_FEED_FILE}: {e}")
    # Disk unreadable or empty — fall back to whatever's in memory.
    with _last_feed_fallback_lock:
        return _last_feed_fallback


def _write_last_feed_time(ts):
    """Persist the supplied datetime to LAST_FEED_FILE AND update the
    in-memory fallback. Returns True if the disk write succeeded; False
    means the value lives only in memory until the next process restart.
    """
    global _last_feed_fallback
    # Always update the in-memory copy first so reads get the new value
    # even if the disk write fails.
    with _last_feed_fallback_lock:
        _last_feed_fallback = ts
    try:
        with open(LAST_FEED_FILE, "w") as f:
            f.write(ts.isoformat())
        return True
    except Exception as e:
        print(f"[FEED_TIMING] Could not write {LAST_FEED_FILE}: {e}")
        system_errors_append(f"Last-feed timestamp write error: {e}")
        return False


def _parse_feed_time(text):
    """Parse a 'HH:MM' string into a (hour, minute) int pair. Returns None
    on any failure so the caller can skip the slot rather than crashing
    the daemon. Tolerant of stray whitespace and out-of-range values.
    """
    try:
        parts = (text or "").strip().split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h < 24 and 0 <= m < 60:
            return (h, m)
    except Exception:
        pass
    return None


def _read_feed_slots():
    """Read the 10 feed_N_enabled / feed_N_time slots from FeedSchedule.
    Returns a list of (slot_index, hour, minute) tuples for enabled,
    well-formed slots only. slot_index is 1..10 (matches the UI labels).
    Re-read fresh on every CheckFeedTiming tick so live edits apply
    without a restart.
    """
    slots = []
    try:
        cfg = load_config()
    except Exception as e:
        print(f"[FEED_TIMING] Could not load config for slot read: {e}")
        return slots
    for i in range(1, 11):
        try:
            if not cfg.getboolean('FeedSchedule', f'feed_{i}_enabled', fallback=False):
                continue
            hm = _parse_feed_time(cfg.get('FeedSchedule', f'feed_{i}_time', fallback=''))
            if hm is None:
                continue
            slots.append((i, hm[0], hm[1]))
        except Exception as e:
            print(f"[FEED_TIMING] Could not read feed slot {i}: {e}")
    return slots


def _next_scheduled_feed_datetime():
    """Return the next datetime at which an enabled feed slot will fire.
    Walks today's enabled slots, picks the soonest one still in the
    future; if all of today's are in the past, returns the earliest
    enabled slot for tomorrow. Returns None if no slots are enabled.
    """
    slots = _read_feed_slots()
    if not slots:
        return None
    now = datetime.now()
    today_candidates = []
    for _, h, m in slots:
        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidate > now:
            today_candidates.append(candidate)
    if today_candidates:
        return min(today_candidates)
    # All of today's enabled slots have already passed — earliest tomorrow.
    earliest_h, earliest_m = min((h, m) for _, h, m in slots)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=earliest_h, minute=earliest_m, second=0, microsecond=0,
    )
    return tomorrow


# Per-slot "last fired on date" tracker. Lives in process memory only —
# resets on every restart. The strict-no-catch-up policy means if the
# system is restarted between (say) 06:00 and 06:05, the 06:00 slot is
# treated as "not yet fired today" because we have no memory of it. The
# guard below ("must be within FEED_TIMING_CATCH_LIMIT_SEC of scheduled
# time") prevents that from causing a delayed fire after a long downtime.
_feed_slot_last_fire_date = {}

# How many seconds after a slot's scheduled moment the daemon is still
# willing to fire it. Larger than the tick interval (FEED_TIMING_CHECK_INTERVAL,
# 60 s) so we never miss a slot due to ordinary scheduling jitter, but small
# enough that a long downtime won't trigger an out-of-time feed when the
# system comes back. 5 minutes is a sensible balance.
FEED_TIMING_CATCH_LIMIT_SEC = 300


def CheckFeedTiming():
    """Daemon loop. Start with threading.Thread(target=CheckFeedTiming, daemon=True).

    Wakes up every FEED_TIMING_CHECK_INTERVAL seconds. Reads the 10
    feed-time slots from [FeedSchedule] each tick. For every enabled slot
    whose scheduled moment has just passed (within FEED_TIMING_CATCH_LIMIT_SEC
    seconds) AND that hasn't already fired today, triggers RunFoodSequence
    and marks the slot fired for today.
    """
    print("[FEED_TIMING] CheckFeedTiming loop started (fixed-time mode)")

    while True:
        try:
            slots = _read_feed_slots()
            if not slots:
                # No enabled slots — automatic feeding is off. Keep polling
                # so re-enabling via the web UI is picked up promptly.
                _refresh_next_feeding_time()
                time.sleep(FEED_TIMING_CHECK_INTERVAL)
                continue

            now = datetime.now()
            today = now.date()

            # For each enabled slot, check if its scheduled time has passed
            # within the catch window AND it hasn't already fired today.
            for slot_index, h, m in slots:
                scheduled = now.replace(hour=h, minute=m, second=0, microsecond=0)
                delta_sec = (now - scheduled).total_seconds()
                if delta_sec < 0:
                    continue  # not yet due
                if delta_sec > FEED_TIMING_CATCH_LIMIT_SEC:
                    continue  # passed during downtime; strict-skip per spec
                if _feed_slot_last_fire_date.get(slot_index) == today:
                    continue  # already fired this slot today

                # Mark fired BEFORE running so a crash mid-cycle doesn't
                # cause a re-fire on the next tick.
                _feed_slot_last_fire_date[slot_index] = today
                print(f"[FEED_TIMING] Slot {slot_index} ({h:02d}:{m:02d}) due "
                      f"({delta_sec:.0f}s after scheduled); firing.")
                log_event(f"Scheduled feed slot {slot_index} ({h:02d}:{m:02d}) firing")
                cycle_start = datetime.now()
                with _feed_lock:
                    try:
                        RunFoodSequence()
                    except Exception as e:
                        print(f"[FEED_TIMING] RunFoodSequence raised (continuing): {e}")
                        traceback.print_exc()
                        system_errors_append(f"RunFoodSequence error: {e}")
                # Persist last-feed time for the home-page display and
                # other consumers of LAST_FEED_FILE. Anchor at cycle start
                # so the value doesn't drift by the cycle's duration.
                _write_last_feed_time(cycle_start)
                # Only one slot per tick — if multiple slots collide on
                # the same minute, the others fire on the next tick (still
                # within the 5-min catch window).
                break

            # Update the home page's "Next Scheduled Feeding" display each tick.
            _refresh_next_feeding_time()

        except Exception as e:
            print(f"[FEED_TIMING] Loop iteration crashed (continuing): {e}")
            traceback.print_exc()
            system_errors_append(f"CheckFeedTiming error: {e}")

        time.sleep(FEED_TIMING_CHECK_INTERVAL)
# end of CheckFeedTiming


# ------------------------------------------------------------------------------
# IdleTubeDry — daemon loop that walks the rotor port-by-port between feeds,
# parking at each port for `minutes` minutes to let the dispense tube dry.
#
# Active conditions (all must hold for the function to do hardware work):
#   - dry_enabled checkbox is True
#   - The next scheduled feed is more than IDLE_DRY_PRE_FEED_GUARD_MIN minutes away
#   - No feed cycle is currently running (enforced via _feed_lock)
#
# Halting:
#   The X-minute wait ALWAYS runs to completion (no mid-wait poll). At each
#   port-move boundary the function re-checks the guard window — if a feed
#   is now imminent, it stops there. This means a worst-case overrun of one
#   X-minute slot before halt, which is acceptable because the lock
#   (acquired below) prevents an actual collision with a feed in progress.
# ------------------------------------------------------------------------------

# How close (in minutes) to a scheduled feed before the dry cycle has to halt.
IDLE_DRY_PRE_FEED_GUARD_MIN = 10
# Cadence of the daemon's outer loop when there's nothing to do (e.g. dry_enabled
# is False, or we're inside the pre-feed guard window). Cheap to poll.
IDLE_DRY_OUTER_TICK_SEC = 30

# Mutual-exclusion lock between IdleTubeDry, RunFoodSequence, manual API
# routes, and the MQTT initFeeder handler is _feed_lock — defined at the
# top of the file with the other module-level locks (so it's visible to
# all callers regardless of source order).
# (The lock previously lived here; moved up at v5.4.)


def _minutes_to_next_feed():
    """Return minutes until the next enabled scheduled feed slot, or None
    if no slots are enabled. Used by the dry cycle's pre-feed guard.
    """
    nxt = _next_scheduled_feed_datetime()
    if nxt is None:
        return None
    return (nxt - datetime.now()).total_seconds() / 60.0


def _refresh_next_feeding_time():
    """Recompute and update the global next_feeding_time string used by the
    home page and /api/status. Called from the config save handler (so the
    value updates immediately on Save) and from CheckFeedTiming's loop (so
    the value stays current as time passes and slots fire).
    """
    global next_feeding_time
    # If a feed/dry cycle is currently running we'd otherwise display the
    # in-progress feed's start time as "next" — confusing. Surface the
    # in-progress state directly. Best-effort: we test the lock without
    # blocking; if we get it we release immediately, so this is just a probe.
    got = _feed_lock.acquire(blocking=False)
    if not got:
        next_feeding_time = "Cycle in progress"
        return
    _feed_lock.release()

    nxt = _next_scheduled_feed_datetime()
    if nxt is None:
        next_feeding_time = "Not scheduled"
        return
    # v7.7: format matches the upper clock display — 12-hour time with
    # AM/PM on the first line (rendered bold by CSS on the home page),
    # DD:MM on the second line (no year). The two lines are joined with
    # a literal newline; the home page renders this with `white-space:
    # pre-line` so the newline becomes a visual line break. Other
    # consumers (MQTT, post-cycle Slack) see the newline as harmless
    # whitespace.
    hour_12 = nxt.hour % 12 or 12   # 0->12, 13->1, etc. (match upper clock JS)
    ampm    = "PM" if nxt.hour >= 12 else "AM"
    next_feeding_time = (
        f"{hour_12}:{nxt.minute:02d}:{nxt.second:02d} {ampm}\n"
        f"{nxt.day:02d}:{nxt.month:02d}"
    )


def _active_tank_ports():
    """Return a sorted list of 1-indexed port numbers (1..60) for tanks
    enabled in TankSettings. Used by IdleTubeDry's "Only dry active tubes"
    mode so the rotor walks only the ports that actually receive food.
    Re-read fresh on each iteration so config changes take effect on the
    next port move (same pattern as tube_dry_time).
    """
    try:
        cfg = load_config()
        return [
            i for i in range(1, 61)
            if cfg.getboolean('TankSettings', f'tank_{i}_enabled', fallback=False)
        ]
    except Exception as e:
        print(f"[IDLE_DRY] Could not read enabled-tank list: {e}")
        return []


def IdleTubeDry(minutes):
    """Daemon loop. Start with threading.Thread(target=IdleTubeDry, args=(<n>,), daemon=True).

    Walks the rotor through ports 1..60 in sequence, sitting at each port
    for the configured tube_dry_time minutes to let the dispense tube dry.

    The `minutes` parameter is the initial value passed in at thread start.
    The actual wait time used at runtime is re-read from the live module
    global `tube_dry_time` on each cycle iteration, so edits through the
    Configuration page take effect on the next port move.

    Lock policy (v5.4): the X-minute wait happens WITHOUT holding _feed_lock,
    so a feed can fire at any time. The lock is acquired only briefly around
    the state-recovery move (HomeRotor + MoveToPortOne if current_port is
    invalid) and the single MovePorts call after each wait. This prevents
    the dry cycle from delaying scheduled feeds by up to tube_dry_time
    minutes (the previous behaviour).
    """
    print(f"[IDLE_DRY] IdleTubeDry loop started with initial minutes={minutes}")

    while True:
        try:
            # Active condition: feature must be enabled.
            if not dry_enabled:
                time.sleep(IDLE_DRY_OUTER_TICK_SEC)
                continue

            # Active condition: must not be inside the pre-feed guard window.
            mins_to_feed = _minutes_to_next_feed()
            if mins_to_feed is not None and mins_to_feed < IDLE_DRY_PRE_FEED_GUARD_MIN:
                time.sleep(IDLE_DRY_OUTER_TICK_SEC)
                continue

            # If we're in an unknown/home state, recover position. Holds the
            # lock briefly for the home + move-to-port-1 commands so a feed
            # can't fire during this short recovery.
            if current_port < 0 or current_port > 59:
                if not _feed_lock.acquire(blocking=False):
                    # Feed in progress; defer the recovery.
                    time.sleep(IDLE_DRY_OUTER_TICK_SEC)
                    continue
                try:
                    print(f"[IDLE_DRY] current_port={current_port} not in 0..59; "
                          "homing and moving to port 1.")
                    HomeRotor()
                    MoveToPortOne()
                finally:
                    _feed_lock.release()

            # In "Only dry active tubes" mode, if we're currently on a port
            # that isn't an enabled tank, skip the wait and reposition first.
            # Otherwise we'd waste a dry cycle on a disabled port.
            if dry_active_only:
                active_ports = _active_tank_ports()
                if active_ports and (current_port + 1) not in active_ports:
                    next_one = next((p for p in active_ports if p > current_port + 1),
                                    active_ports[0])
                    steps = _ports_forward(current_port, next_one)
                    if steps > 0:
                        if not _feed_lock.acquire(blocking=False):
                            time.sleep(IDLE_DRY_OUTER_TICK_SEC)
                            continue
                        try:
                            print(f"[IDLE_DRY] active-only: current port "
                                  f"{current_port + 1} not enabled; "
                                  f"jumping {steps} port(s) to {next_one}")
                            MovePorts(steps)
                        finally:
                            _feed_lock.release()
                    # Loop around so the now-current port gets logged + waited.
                    continue

            # Wait at the current port for the configured number of minutes.
            # Re-read tube_dry_time fresh each iteration so live edits take effect.
            # The lock is NOT held during this sleep, so a scheduled feed can
            # fire whenever it's due.
            current_minutes = max(0, int(tube_dry_time))
            print(f"[IDLE_DRY] Drying at port {current_port + 1} "
                  f"for {current_minutes} minute(s)")
            log_event(f"Tube drying at port {current_port + 1} for {current_minutes} min")
            time.sleep(current_minutes * 60)

            # Wait completed. Re-check the guard window before moving —
            # if a feed is now imminent, halt here without commanding the rotor.
            mins_to_feed = _minutes_to_next_feed()
            if mins_to_feed is not None and mins_to_feed < IDLE_DRY_PRE_FEED_GUARD_MIN:
                print(f"[IDLE_DRY] Feed in {mins_to_feed:.1f} min (< guard); "
                      "halting before next port move.")
                # Outer loop will re-evaluate conditions next tick.
                continue

            # Acquire the lock briefly just for the port move. If a feed
            # cycle is currently running we'll be blocked here until it
            # completes, then we'll do the move and continue.
            with _feed_lock:
                # Re-confirm conditions inside the lock — they may have
                # changed while we were waiting for the lock.
                if not dry_enabled:
                    continue

                if dry_active_only:
                    # Walk only the enabled-tank ports (read fresh each time
                    # so config changes apply on the next move).
                    active_ports = _active_tank_ports()
                    if not active_ports:
                        # No tanks enabled — nothing to dry. Sit at the
                        # current port and let the outer tick re-evaluate.
                        print("[IDLE_DRY] active-only mode but no tanks enabled; "
                              "skipping move and waiting next tick.")
                        continue
                    # Find the next active port AFTER current_port (1-indexed
                    # comparison). Wrap to the first if we're past the last.
                    current_one = current_port + 1
                    next_one = next((p for p in active_ports if p > current_one),
                                    active_ports[0])
                    steps = _ports_forward(current_port, next_one)
                    if steps > 0:
                        print(f"[IDLE_DRY] active-only: moving {steps} port(s) "
                              f"to next enabled tank {next_one}")
                        MovePorts(steps)
                    # If steps == 0 we're already on the only enabled port;
                    # just wait again next iteration.
                else:
                    # Original behaviour — step forward one port at a time.
                    MovePorts(1)

        except Exception as e:
            print(f"[IDLE_DRY] Loop iteration crashed (continuing): {e}")
            traceback.print_exc()
            system_errors_append(f"IdleTubeDry error: {e}")
            time.sleep(IDLE_DRY_OUTER_TICK_SEC)
# end of IdleTubeDry


# home the rotor to the opto sensor, then move it out of home and back in (slower)
def HomeRotor():
    global current_port # port number
    print("[HARDWARE] Homing Rotor")
    opto_rot = GPIO.input(23) # 23 is rotor OPTO
    if opto_rot ==GPIO.LOW:
        print("-HOME flag found at start")
    else:
        print("-HOME flag NOT found at start")
       
    print("Commanding home")
    time.sleep(0.5)
    _serial_write("/1Z100000R\r")
    for x in range(2500):
        opto_rot = GPIO.input(23) # 23 is rotor OPTO, 25 is air sense
        if opto_rot ==GPIO.LOW:
            print("Found home sensor")
            break
        time.sleep(0.05)
    opto_rot = GPIO.input(23) # 23 is rotor OPTO
    print("Moving in and out of home again")
    _serial_write("/1Z100000R\r")
    time.sleep(2)
    current_port = 100 # 99 is unknown, 0 to 59 is ports 1 to 60. At home the value is set to 100
    print("[HARDWARE] Home complete")
# rotor now at home, completed

# Move from home to port 1 (this is a calibrated value)
def MoveToPortOne():
    global current_port
    print("[HARDWARE] Moving the rotor to port one")
    _serial_write(f"/1P{MICROSTEPS_TO_PORT_ONE}R\r")
    time.sleep(6) # 6 second delay, this is fixed for the move from home to port 1
    current_port = 0 # 99 is unknown, 0 to 59 is ports 1 to 60. At home the value is set to 100
    print("[HARDWARE] Rotor at Port one")
# rotor now at port 1

# using the camera and code, calculate the remaining food level
def CheckFoodLevel():
    """Trigger an immediate food-level analysis so the manual button gives
    a fresh reading rather than waiting for the background thread's next pass.
    """
    print("[HARDWARE] Checking the food level")
    _run_food_analysis_from_camera()

# use the vibration motor to settle the food for a fixed amount of time, motor is off at the end
def SettleMotor(settle_time): # vibrate/settle the food for a fixed time
    print("[HARDWARE] Settling the food")
    print(f"[HARDWARE] Settle time: {settle_time}")
    # turn on the food settle vibration motor, vib is time in seconds
    GPIO.output(13, GPIO.HIGH) # turn on the vibration motor
    time.sleep(settle_time)
    GPIO.output(13, GPIO.LOW) # turn off the vibration motor
    print("[HARDWARE] Settled the food")
# end of motor vibe settle food

# change the state of the settle motor, motor can be on or off at the end of the function
def SettleMotorState(state): # turn the settle motor on or off, used to allow other things to happen in parallel
    print(f"[HARDWARE] Setting the settle motor: {state}")
    GPIO.output(13, state) # set the motor state
    print("[HARDWARE] Settle motor state set")
# end of motor settle on or off function

# read the temperature and humidity in the air supply
def ReadTempHum(): # read and return the temperature and humidity
    """Read the AHTx0 temperature/humidity sensor over I2C. On failure
    (sensor unavailable, I2C glitch) we keep the previous values rather
    than crashing — the web UI will show stale numbers, which is better
    than 500ing.
    """
    global current_temperature, current_humidity
    print("[HARDWARE] Reading the air temperature and humidity")
    if sensor is None:
        print("[HARDWARE] Sensor unavailable — keeping previous temp/hum values")
        return
    try:
        t = sensor.temperature
        h = sensor.relative_humidity
        print("\nTemperature: %0.1f C" % t)
        print("Humidity: %0.1f %%" % h)
        print(" ")
        current_temperature = round(t, 1)
        current_humidity = round(h, 2)
        print("[HARDWARE] Air temperature and humidity updated")
    except Exception as e:
        print(f"[HARDWARE] Temp/hum read failed: {e}")
        system_errors_append(f"Temp/hum read error: {e}")
# read temperature and humidity end

# send commands to the allmotion drivers to set their parameters, after cold powerup
def SetupSystemBoot():
    global current_port
    print("[HARDWARE] Setting up the system from boot")
    if ser is None:
        msg = ("SetupSystemBoot: serial port unavailable; motor commands will "
               "be silently dropped. Check /dev/serial0 and the EZ17 wiring.")
        print(f"[HARDWARE] WARNING: {msg}")
        system_errors_append(msg)
        try:
            send_slack_notification("⚠ Feeder boot: serial port unavailable; motors offline")
        except Exception:
            pass
        # Continue anyway — the rest of startup (config, web UI, etc.) may
        # still be useful for diagnosis.
    # setup here:
    print("Running allmotion driver setup")
    _serial_write("/1TR\r")  # reset #1 ROTOR
    time.sleep(command_delay) # wait for serial
    _serial_write("/2TR\r")  # reset #2 HOPPER
    time.sleep(command_delay) # wait for serial
    _serial_write("/1V1200L20m55h20j32R\r")
    time.sleep(command_delay) # wait for serial
    _serial_write("/2V600L150m80h5j2R\r")
    time.sleep(command_delay) # wait for serial
    _serial_write("/1F1R\r")  # reverse the rotor motor direction due to the pulley
    time.sleep(command_delay) # wait for serial
    print("[HARDWARE] allmotion setup complete")
    current_port = 99 # 99 is unknown, 0 to 59 is ports 1 to 60. At home the value is set to 100
    time.sleep(0.5) # small pause
# end of setup motor driver boards

# move the rotor by a set number of ports, defined by port number
def MovePorts(port_number):
    """Move the rotor port_number forward, updating current_port. The
    function only operates from a known position (current_port 0..59);
    home (100) and unknown (99) are rejected because the modular
    arithmetic below would silently produce wrong results.
    """
    global current_port
    print("[HARDWARE] Moving a number of ports")
    print(f"[HARDWARE] Ports to move: {port_number}")
    if current_port < 0 or current_port > 59:
        msg = (f"MovePorts refused — current_port = {current_port} "
               "(home/unknown). Call MoveToPortOne() first.")
        print(f"[HARDWARE] {msg}")
        raise RuntimeError(msg)
    scale = 832.22 # floating point of 1 port microsteps, confirmed
    timeScale = 0.85 # time scale to wait per single port
    step_int = int(scale * port_number)
    string_to_send = f"/1P{step_int}R\r"
    _serial_write(string_to_send) # Send the complete string command
    time.sleep(timeScale*port_number) # delay, calculated per port value
    # Wrap-aware update: current_port is 0..59 (port 1..60). After moving
    # `port_number` ports forward we land at (current + n) mod 60. The
    # previous version had `< 61` which let current_port reach 60, an
    # invalid state. Fixed in v5.4.
    current_port = (current_port + port_number) % 60
    print("[HARDWARE] Rotor moved ", port_number, "ports")
    print("[HARDWARE] Current port ", current_port)
# end of the move to ports function

# moves the rotor back and forth rapidly, jiggle_count is how many times, jiggle_intensity is the number of microsteps
def JiggleRotor(jiggle_count, jiggle_intensity):
    print("[HARDWARE] Jiggling the rotor")
    print(f"[HARDWARE] Count: {jiggle_count}, Intensity: {jiggle_intensity}")
    time_scale = 500 # scalar to turn the intensity value in a time delay to wait
    time_move = jiggle_intensity / time_scale # calc the time to wait for the move to finish
    backward_jiggle = f"/1D{jiggle_intensity}R\r"
    forward_jiggle  = f"/1P{jiggle_intensity}R\r"
    # nominal intensity of jiggle 200
    for x in range(jiggle_count):
        _serial_write(backward_jiggle)
        time.sleep(time_move)
        _serial_write(forward_jiggle)
        time.sleep(time_move)
    print("[HARDWARE] Jiggle the rotor complete")
# end of jiggle function

def BlowAir(duration):
    """Pulse the air solenoid for `duration` seconds (blocking).
    Used for fixed on/off bursts with nothing else happening in between.
    """
    print("[HARDWARE] Blowing the air solenoid fixed period")
    print(f"[HARDWARE] Duration (s): {duration}")
    GPIO.output(6, GPIO.HIGH) # turn on the air solenoid
    time.sleep(duration)
    GPIO.output(6, GPIO.LOW) # turn off the air solenoid
    print("[HARDWARE] air blown")
# end of the blow air function

def BlowAirLong(state): # this is used for turning on the air, doing something else then turning it off
    print(f"[HARDWARE] Turning the air solenoid: {state}")
    GPIO.output(6, GPIO.HIGH if state else GPIO.LOW)  # turn on or off, air solenoid
    print("[HARDWARE] air state changed")


def CountHopperScrew(time_long):
    """Count slot passes over time_long seconds.
    Returns slot passes (edges // 2) preserving the original function's units.
    """
    print("[HARDWARE] Counting the hopper screw turns")
    print("Reading the thread opto via edge interrupt")
    global glob_food_tn, _edge_count
    # Reset the edge counter atomically so an in-flight increment in the
    # polling thread can't race the reset.
    with _edge_count_lock:
        _edge_count = 0
    time.sleep(time_long)
    with _edge_count_lock:
        edges = _edge_count
    tot_count = edges // 2  # slot passes, matches original counting semantics
    glob_food_tn += tot_count  # add the tot_count value to global counter
    return tot_count


def LoadFood(amount):
    print("[HARDWARE] Loading the food")
    print(f"[HARDWARE] Amount: {amount}")
    if amount == 0:
        print("quantity is ZERO for this tank, so no food sent")
        return
    global food_ratio, _edge_count
    food_ratio = 0  # reset the food check ratio
    print("Loading food ", amount, "mg")
    _serial_write("/2z10000R\r")  # reset the virtual position, 10000
    time.sleep(command_delay)
    steps = int(amount * food_scale)  # calc the number of steps based off food scale integer
    if steps == 0:
        print("calculated steps = 0 (amount * food_scale rounded to zero); skipping move")
        return
    # Rev14: P instead of D would reverse the motor direction
    command_string = f"/2D{steps}R\r"
    # Reset the edge counter atomically (race-safe vs the polling thread)
    # immediately before issuing the move so we capture only this run's edges.
    with _edge_count_lock:
        _edge_count = 0
    _serial_write(command_string)
    # Motor runs at 600 microsteps/sec, so steps/600 = run time. +1 s safety.
    time_load = round((steps / 600) + 1, 1)
    time.sleep(time_load)  # wait for the move to complete while polling thread counts edges
    with _edge_count_lock:
        edges_now = _edge_count
    # Slot passes (6-slot disc => 12 edges/rev). Drop the // 2 if calibration expects raw edges.
    value = edges_now // 2
    expected = steps / 200  # 200 from empirical calibration ("200 from 99.9")
    print("CALC VAL ", expected)
    print("VALUE ", value)
    food_ratio = round(value / expected, 2)
    print("Food ratio (ideally 1) = ", food_ratio)
# end of the load food function


# Clean the rotor by spinning it by clean_cycles with the air ON
def CleanRotor(clean_cycles):
    print("[HARDWARE] Cleaning the rotor")
    print(f"[HARDWARE] Cycles: {clean_cycles}")
    HomeRotor()                # home the rotor
    MoveToPortOne()            # move the rotor from home to port 1
    BlowAirLong(GPIO.HIGH)     # air solenoid HIGH/ON
    for _ in range(clean_cycles):
        HomeRotor()       # home rotor
        time.sleep(1)
        MoveToPortOne()   # move the rotor from home to port 1
        time.sleep(1)
    BlowAirLong(GPIO.LOW)      # air solenoid LOW/OFF
    print("[HARDWARE] Cleaning the rotor completed")

# Drive the food-tube backlight LED on or off via MOSFET on GPIO 12.
def LightTube(state):
    print("[HARDWARE] Changing the food light on/off")
    print(f"[HARDWARE] State: {state}")
    GPIO.output(12, GPIO.HIGH if state else GPIO.LOW) # Change the LED state
    print("[HARDWARE] Changed the food light")

def runFoodSchedule(*args, **kwargs):
    """REMOVED — was a stub that never did anything. Scheduled feeds are
    now driven by CheckFeedTiming -> RunFoodSequence. Kept as a backwards-
    compatible no-op in case any external code references the name.
    """
    print("[SCHEDULE] runFoodSchedule no longer used — see CheckFeedTiming + RunFoodSequence")


def immediateFoodNow(tank_checkboxes, tank_food_amounts):
    """Trigger an immediate feed using the values supplied from the
    Immediate Feed web form.

    The form values are written to the ImmediateFeed config section so they
    persist across reloads of the Immediate Feed page (and only that page).
    Crucially we do NOT touch TankSettings — that section is owned by the
    Fish Feeder Configuration page and drives scheduled feeds; clobbering
    it here would silently overwrite the user's saved schedule (this was
    the v5.4–v5.5 bug). RunFoodSequence is called with tank_section pointed
    at ImmediateFeed so the per-tank loop reads from the right place.
    """
    print("[IMMEDIATE] immediateFoodNow called — delegating to RunFoodSequence")
    print(f"[IMMEDIATE] Enabled tanks: {sum(tank_checkboxes)}")
    log_event(f"Immediate feed requested ({sum(tank_checkboxes)} tank(s))")

    # Persist the immediate-feed selections into the ImmediateFeed section
    # (this section is independent of TankSettings used by the scheduler).
    try:
        cfg = load_config()
        if 'ImmediateFeed' not in cfg:
            cfg['ImmediateFeed'] = {}
        for i in range(60):
            cfg['ImmediateFeed'][f'tank_{i+1}_enabled'] = str(tank_checkboxes[i]).lower()
            cfg['ImmediateFeed'][f'tank_{i+1}_food_mg'] = str(tank_food_amounts[i])
        save_config(cfg)
    except Exception as e:
        print(f"[IMMEDIATE] Could not stage immediate feed config: {e}")
        send_slack_notification(f"Immediate feed aborted — config write failed: {e}")
        return

    # Run the feed under the shared serial lock so we don't collide with
    # the IdleTubeDry daemon or any other rotor user. Pass tank_section so
    # RunFoodSequence reads from ImmediateFeed instead of TankSettings.
    with _feed_lock:
        try:
            RunFoodSequence(tank_section='ImmediateFeed')
        except Exception as e:
            print(f"[IMMEDIATE] RunFoodSequence raised: {e}")
            traceback.print_exc()
            system_errors_append(f"Immediate feed error: {e}")


# ==============================================================================
# CAMERA FUNCTIONS
# ==============================================================================

def get_camera():
    """
    Returns a shared Picamera2 instance, initialising it on first call.
    Uses a lock so concurrent requests don't create multiple instances.

    Inputs: None
    Outputs: Picamera2 instance, or None if camera is unavailable
    """
    global picam2_instance
    with camera_lock:
        if picam2_instance is None:
            from picamera2 import Picamera2

            def _attempt_init():
                """Build, configure, and start a new Picamera2. Returns the instance or raises."""
                inst = Picamera2()
                # Configure a single main stream at the full snapshot resolution.
                # We downsize in PIL for the preview stream — that's much more
                # reliable than configuring a separate lores stream, which on
                # many picamera2 versions is restricted to YUV420 only and
                # silently rejects BGR888. At 1 fps the resize cost is trivial.
                # Note: picamera2's "BGR888" format actually delivers R,G,B
                # channel ordering to numpy/PIL (libcamera naming quirk), so
                # PIL sees true RGB without any manual channel swap.
                cfg = inst.create_video_configuration(
                    main={"size": (CAMERA_SNAP_WIDTH, CAMERA_SNAP_HEIGHT), "format": "BGR888"}
                )
                inst.configure(cfg)
                inst.start()
                time.sleep(0.5)  # Let sensor settle after start
                return inst

            print("[CAMERA] Initialising camera...")
            try:
                picam2_instance = _attempt_init()
                print("[CAMERA] Camera ready")
            except Exception as e:
                err_msg = str(e)
                print(f"[CAMERA] Initial init failed: {err_msg}")
                # Detect the "stuck in Acquired state" symptom — left over from
                # a previous process that didn't release the camera cleanly.
                # Try to force-release it and retry once.
                if "Acquired" in err_msg or "acquire" in err_msg.lower():
                    print("[CAMERA] Camera appears stuck in Acquired state. Attempting recovery...")
                    # Try to close whatever partially-created instance exists
                    try:
                        # A Picamera2() constructor can leave an object behind even on failure
                        tmp = Picamera2()
                        try:
                            tmp.stop()
                        except Exception:
                            pass
                        try:
                            tmp.close()
                        except Exception:
                            pass
                    except Exception as recover_err:
                        print(f"[CAMERA] Recovery close attempt: {recover_err}")
                    time.sleep(2.0)  # Give libcamera time to release
                    print("[CAMERA] Retrying camera init...")
                    try:
                        picam2_instance = _attempt_init()
                        print("[CAMERA] Camera ready (after recovery)")
                    except Exception as retry_err:
                        print(f"[CAMERA] Retry also failed: {retry_err}")
                        system_errors_append(f"Camera init error (after retry): {retry_err}")
                        picam2_instance = None
                else:
                    system_errors_append(f"Camera init error: {e}")
                    picam2_instance = None
    return picam2_instance


def generate_mjpeg_stream():
    """
    Generator function that yields MJPEG frames from the camera.
    Each frame is yielded as a multipart HTTP response chunk.

    Inputs: None (uses global camera instance)
    Outputs: Generator of bytes (MJPEG multipart frames)
    """
    cam = get_camera()
    if cam is None:
        # Yield a single grey placeholder frame so the <img> tag shows
        # something rather than a broken-image icon.
        placeholder = Image.new("RGB", (CAMERA_STREAM_WIDTH, CAMERA_STREAM_HEIGHT), color=(60, 60, 60))
        buf = io.BytesIO()
        placeholder.save(buf, format="JPEG", quality=70)
        frame_bytes = buf.getvalue()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        return

    try:
        while True:
            # Capture from the main (full-res) stream, then downsize for preview.
            # At 1 fps the resize is cheap and eliminates the lores-format risk.
            frame_array = cam.capture_array("main")
            img = Image.fromarray(frame_array)
            # Downsize to preview resolution
            img = img.resize((CAMERA_STREAM_WIDTH, CAMERA_STREAM_HEIGHT), Image.BILINEAR)
            # Crop left and right edges
            w, h = img.size
            img = img.crop((CAMERA_CROP_LEFT, 0, w - CAMERA_CROP_RIGHT, h))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            frame_bytes = buf.getvalue()

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

            # Throttle to the configured framerate
            time.sleep(1.0 / CAMERA_FRAMERATE)

    except GeneratorExit:
        # Client disconnected — nothing to clean up here; camera stays open
        print("[CAMERA] Stream client disconnected")
    except Exception as e:
        print(f"[CAMERA] Stream error: {e}")
        system_errors_append(f"Camera stream error: {e}")


def capture_snapshot():
    """
    Captures a single JPEG snapshot from the camera.

    Inputs: None
    Outputs: bytes (JPEG image data), or None on failure
    """
    cam = get_camera()
    if cam is None:
        print("[CAMERA] Snapshot requested but camera is unavailable")
        return None

    try:
        # Capture from the main (full-res) stream for maximum quality
        print("[CAMERA] Capturing full-res snapshot...")
        t_start = time.time()
        # Turn on the food-tube backlight for the capture, preserving the prior
        # manual-toggle state so we can restore it afterwards.
        _prior_light = food_light_state
        try:
            LightTube(True)
            time.sleep(0.05)  # let the LED physically turn on
            # Flush stale frames captured before the LED was on (same fix as
            # _run_food_analysis_from_camera). Without this, snapshots can be
            # pre-illumination dark frames.
            for _ in range(5):
                cam.capture_array("main")
            frame_array = cam.capture_array("main")
        finally:
            LightTube(_prior_light)
        print(f"[CAMERA] Frame captured in {time.time() - t_start:.2f}s, shape={frame_array.shape}, dtype={frame_array.dtype}")
        img = Image.fromarray(frame_array)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        jpeg_bytes = buf.getvalue()
        print(f"[CAMERA] Snapshot encoded: {len(jpeg_bytes)} bytes, total {time.time() - t_start:.2f}s")
        return jpeg_bytes
    except Exception as e:
        print(f"[CAMERA] Snapshot error: {e}")
        traceback.print_exc()
        system_errors_append(f"Camera snapshot error: {e}")
        return None


def _shutdown_camera():
    """
    Clean up the camera on process exit.
    Releases libcamera's exclusive hold so the next run can acquire it.
    Registered via atexit below.
    """
    global picam2_instance
    with camera_lock:
        if picam2_instance is not None:
            print("[CAMERA] Shutting down camera cleanly...")
            try:
                picam2_instance.stop()
            except Exception as e:
                print(f"[CAMERA] stop() during shutdown: {e}")
            try:
                picam2_instance.close()
            except Exception as e:
                print(f"[CAMERA] close() during shutdown: {e}")
            picam2_instance = None
            print("[CAMERA] Camera released")


atexit.register(_shutdown_camera)


# ==============================================================================
# FOOD LEVEL ANALYSIS (migrated from v3.4)
# ==============================================================================

def _apply_crop(img):
    """Crop a PIL Image using the configured FOOD_CROP_* constants."""
    w, h = img.size
    top    = max(0, min(FOOD_CROP_TOP,    h - 1))
    bottom = max(0, min(FOOD_CROP_BOTTOM, h - 1 - top))
    left   = max(0, min(FOOD_CROP_LEFT,   w - 1))
    right  = max(0, min(FOOD_CROP_RIGHT,  w - 1 - left))
    return img.crop((left, top, w - right, h - bottom))


def _pil_to_cv2_bgr(pil_img):
    """Convert a PIL RGB image to an OpenCV BGR ndarray."""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def analyze_food_level(
    image,
    roi,
    full_x,
    empty_x,
    threshold=None,
    smoothing_ratio=40,
    debug=False,
):
    """
    Analyse a backlit tube image and return the food fill level as a percentage.

    The tube is illuminated from behind. Where food is present the pixels are
    dark; where the tube is empty the pixels are bright. The function averages
    brightness column-by-column inside a horizontal ROI strip, detects the
    dark/bright boundary, and maps its position between the two reference lines.

    Parameters
    ----------
    image : np.ndarray | str
        BGR image array (H x W x 3) or a file-path string.
    roi : tuple[int, int, int, int]
        (x1, y1, x2, y2) pixel bounding box of the analysis strip.
    full_x : int
        X pixel coordinate of the 'full' reference line (100 %).
    empty_x : int
        X pixel coordinate of the 'empty' reference line (0 %).
    threshold : int | None
        Grayscale separator between food (dark) and empty (bright).
        None → automatic Otsu threshold.
    smoothing_ratio : int
        Kernel size = strip_width // ratio. Larger = smoother signal.
    debug : bool
        Returns a dict with intermediate data when True.

    Returns
    -------
    float  Food level in [0.0, 100.0].
    """
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise FileNotFoundError(f"Could not read image: {image!r}")
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    x1, y1, x2, y2 = roi
    strip_bgr = image[y1:y2, x1:x2]
    gray = cv2.cvtColor(strip_bgr, cv2.COLOR_BGR2GRAY)

    if gray.size == 0:
        raise ValueError("ROI produces an empty crop — check roi coordinates.")

    col_mean   = gray.mean(axis=0).astype(np.float32)
    k          = max(3, len(col_mean) // smoothing_ratio)
    col_smooth = np.convolve(col_mean, np.ones(k) / k, mode="same")

    if threshold is None:
        thresh_val, _ = cv2.threshold(gray, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        thresh_val = float(threshold)

    is_food  = col_smooth < thresh_val
    n_cols   = len(col_smooth)
    full_loc  = int(np.clip(full_x  - x1, 0, n_cols - 1))
    empty_loc = int(np.clip(empty_x - x1, 0, n_cols - 1))
    lo, hi    = min(full_loc, empty_loc), max(full_loc, empty_loc)
    span      = hi - lo

    if span == 0:
        return {"percentage": 0.0, "warning": "full_x == empty_x"} if debug else 0.0

    food_in_span = is_food[lo : hi + 1]

    # Walk inward from the 'full' reference through consecutive food (dark)
    # pixels, stopping at the first bright pixel — the real food/air boundary.
    #
    # This replaces an earlier heuristic that used the first/last dark index
    # in the span. That heuristic was fooled whenever a stray dark speck
    # appeared on the 'empty' side of the strip (tube labels, holder shadows,
    # the tube's bottom ring, dust, minor glare variation): it would read the
    # speck as though food extended all the way across to the full reference,
    # so a physically-empty tube could report as nearly full.
    #
    # Requiring the dark region to be anchored at the full reference means:
    #   * Truly empty tube          → pixel at the full side is bright, walk
    #                                 stops at 0 → 0 %.
    #   * Empty + stray dark speck  → full-side pixels are still bright, speck
    #                                 on the empty side is ignored → 0 %.
    #   * Partial fill              → walk measures how far the food mass
    #                                 actually extends from the full side.
    #   * Full tube                 → walk consumes the entire span → 100 %.
    boundary_offset = 0
    if full_loc <= empty_loc:
        # Full reference on the LEFT of the span — walk rightward from the left end.
        for i in range(len(food_in_span)):
            if food_in_span[i]:
                boundary_offset += 1
            else:
                break
    else:
        # Full reference on the RIGHT of the span — walk leftward from the right end.
        for i in range(len(food_in_span) - 1, -1, -1):
            if food_in_span[i]:
                boundary_offset += 1
            else:
                break

    percentage = float(np.clip(boundary_offset / span * 100.0, 0.0, 100.0))

    if debug:
        return {
            "percentage":      percentage,
            "threshold":       thresh_val,
            "full_loc":        full_loc,
            "empty_loc":       empty_loc,
            "span_px":         span,
            "boundary_offset": boundary_offset,
            "col_smooth":      col_smooth,
            "is_food":         is_food,
        }
    return percentage


def _run_food_analysis_from_camera():
    """
    Capture a single stream frame, run analyze_food_level on it, and
    update both the shared result dict and the global food_percentage.
    Called by the background analysis thread.
    """
    global food_percentage

    cam = get_camera()
    if cam is None:
        with _food_analysis_lock:
            _last_food_analysis_result.update({
                "percentage": None,
                "timestamp":  datetime.now().strftime("%H:%M:%S"),
                "error":      "Camera unavailable",
            })
        return

    try:
        # Turn on the food-tube backlight for the capture, preserving the prior
        # manual-toggle state so we can restore it afterwards.
        _prior_light = food_light_state
        try:
            LightTube(True)
            time.sleep(0.05)  # let the LED physically turn on
            # Flush stale frames captured before the LED was on. Picamera2
            # keeps several buffered frames in flight, so capture_array() can
            # return a pre-illumination (dark) frame — which the analyzer
            # interprets as "all food" → 100%. Discarding a handful of frames
            # guarantees the next capture is a properly lit one.
            for _ in range(5):
                cam.capture_array("main")
            frame_array = cam.capture_array("main")
        finally:
            LightTube(_prior_light)
        pil_img = Image.fromarray(frame_array)
        # V2.6 configures the camera at full snapshot resolution, while the
        # FOOD_* calibration values were captured at stream resolution. Downsize
        # first so FOOD_ROI / FOOD_FULL_X / FOOD_EMPTY_X stay valid.
        pil_img = pil_img.resize((CAMERA_STREAM_WIDTH, CAMERA_STREAM_HEIGHT), Image.BILINEAR)
        pil_img = _apply_crop(pil_img)
        bgr_img = _pil_to_cv2_bgr(pil_img)

        pct = analyze_food_level(
            image=bgr_img,
            roi=FOOD_ROI,
            full_x=FOOD_FULL_X,
            empty_x=FOOD_EMPTY_X,
            threshold=FOOD_THRESHOLD,
        )

        food_percentage = pct  # update global used by home page & MQTT status

        with _food_analysis_lock:
            _last_food_analysis_result.update({
                "percentage": round(pct, 1),
                "timestamp":  datetime.now().strftime("%H:%M:%S"),
                "error":      None,
            })

        print(f"[FOOD] Level updated: {pct:.1f}%")

    except Exception as e:
        print(f"[FOOD] Analysis failed: {e}")
        system_errors_append(f"Food analysis error: {e}")
        with _food_analysis_lock:
            _last_food_analysis_result.update({
                "percentage": None,
                "timestamp":  datetime.now().strftime("%H:%M:%S"),
                "error":      str(e),
            })


def _food_analysis_loop():
    """Background daemon thread — runs analysis every FOOD_ANALYSIS_INTERVAL s.

    Each iteration is wrapped so a single failure in _run_food_analysis_from_camera
    can't kill the thread permanently and silently stop food-level updates.
    Repeat errors of the same type are de-duplicated in system_errors so a
    permanently broken camera doesn't flood the log (would otherwise add an
    entry every 30 s, evicting useful older entries).
    """
    last_logged_error = None
    while True:
        try:
            _run_food_analysis_from_camera()
            last_logged_error = None  # success — clear the dedupe state
        except Exception as e:
            err_key = f"{type(e).__name__}: {e}"
            print(f"[FOOD] Loop iteration crashed (continuing): {e}")
            if err_key != last_logged_error:
                system_errors_append(f"Food analysis loop error: {err_key}")
                last_logged_error = err_key
        time.sleep(FOOD_ANALYSIS_INTERVAL)


# ==============================================================================
# TEMPERATURE / HUMIDITY HOURLY LOGGER
# ==============================================================================

def _read_temp_hum_log():
    """Return the rows currently on disk as a list of {ts, temp, hum} dicts.
    Missing or unreadable file returns an empty list (the page will say so).
    """
    rows = []
    if not os.path.exists(TEMP_HUM_LOG_FILE):
        return rows
    try:
        with open(TEMP_HUM_LOG_FILE, "r") as f:
            # Skip header if present (we always write one).
            first = True
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if first:
                    first = False
                    if line.lower().startswith("timestamp"):
                        continue
                parts = line.split(",")
                if len(parts) < 3:
                    continue
                try:
                    rows.append({
                        "ts":   parts[0],
                        "temp": float(parts[1]),
                        "hum":  float(parts[2]),
                    })
                except ValueError:
                    # Skip malformed lines instead of failing the whole read.
                    continue
    except Exception as e:
        print(f"[LOG] Could not read {TEMP_HUM_LOG_FILE}: {e}")
        system_errors_append(f"Temp/hum log read error: {e}")
    return rows


def _write_temp_hum_log(rows):
    """Atomically rewrite the log with the supplied rows, header included."""
    try:
        tmp = TEMP_HUM_LOG_FILE + ".tmp"
        with open(tmp, "w") as f:
            f.write("timestamp,temperature_c,humidity_pct\n")
            for r in rows:
                f.write(f'{r["ts"]},{r["temp"]},{r["hum"]}\n')
        os.replace(tmp, TEMP_HUM_LOG_FILE)
    except Exception as e:
        print(f"[LOG] Could not write {TEMP_HUM_LOG_FILE}: {e}")
        system_errors_append(f"Temp/hum log write error: {e}")


def _seed_temp_hum_log_if_empty():
    """If the on-disk log doesn't exist yet (first boot), pre-fill it with
    TEMP_HUM_LOG_RETENTION rows of default values. Timestamps are spaced
    one hour apart, ending at "now" — so the chart looks like 5 days of
    history at 22 °C / 40 % from the very first page load. Each hourly
    sample after that replaces the oldest seed row with a real reading,
    so the chart smoothly fills in with measurements over time.
    """
    if os.path.exists(TEMP_HUM_LOG_FILE):
        return  # already have data, nothing to do
    print("[LOG] Pre-seeding temp/hum log with default values "
          f"({TEMP_HUM_LOG_RETENTION} hourly slots, "
          f"{TEMP_HUM_DEFAULT_TEMP}°C / {TEMP_HUM_DEFAULT_HUM}%)")
    now = datetime.now()
    rows = []
    for i in range(TEMP_HUM_LOG_RETENTION):
        # i=RETENTION-1 -> now, i=0 -> RETENTION-1 hours ago
        ts = now - timedelta(hours=(TEMP_HUM_LOG_RETENTION - 1 - i))
        rows.append({
            "ts":   ts.strftime("%Y-%m-%d %H:%M:%S"),
            "temp": TEMP_HUM_DEFAULT_TEMP,
            "hum":  TEMP_HUM_DEFAULT_HUM,
        })
    _write_temp_hum_log(rows)


def _append_temp_hum_sample():
    """Take a fresh sensor reading and write it into the rolling log.

    The list is treated as a sliding window of TEMP_HUM_LOG_RETENTION rows.
    Each call drops the oldest row and appends a new one with the current
    timestamp, so over the first 5 days of operation the seeded defaults
    are gradually replaced by real readings (oldest seed replaced first),
    and from then on it's a continuously rolling window of real data.
    """
    ReadTempHum()  # populates current_temperature / current_humidity
    rows = _read_temp_hum_log()
    rows.append({
        "ts":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "temp": current_temperature,
        "hum":  current_humidity,
    })
    if len(rows) > TEMP_HUM_LOG_RETENTION:
        rows = rows[-TEMP_HUM_LOG_RETENTION:]  # drop oldest, keep last N
    _write_temp_hum_log(rows)
    print(f"[LOG] Appended temp/hum sample ({len(rows)} now on file)")


def _temp_hum_log_loop():
    """Background daemon thread — appends a temp/hum sample every
    TEMP_HUM_LOG_INTERVAL s.

    On startup, pre-seeds the log with default values if no file exists yet,
    so the page has 5 days of placeholder history immediately. After that,
    one real sample per hour replaces the oldest entry on each tick.

    Wrapped per iteration so a transient sensor or filesystem error doesn't
    kill the logger thread.
    """
    try:
        _seed_temp_hum_log_if_empty()
    except Exception as e:
        print(f"[LOG] Could not seed temp/hum log (continuing): {e}")
        system_errors_append(f"Temp/hum log seed error: {e}")

    while True:
        # Wait first so the seeded "now" timestamp isn't immediately
        # bumped out by a real reading on second 0. Real samples land
        # at +1h, +2h, ..., naturally replacing the oldest seed each hour.
        time.sleep(TEMP_HUM_LOG_INTERVAL)
        try:
            _append_temp_hum_sample()
        except Exception as e:
            print(f"[LOG] Temp/hum log iteration crashed (continuing): {e}")
            system_errors_append(f"Temp/hum log loop error: {e}")


# ==============================================================================
# MQTT FUNCTIONS
# ==============================================================================

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected to broker at {MQTT_BROKER_IP}")
        client.subscribe(MQTT_COMMAND_TOPIC, qos=MQTT_QOS)
        print(f"[MQTT] Subscribed to {MQTT_COMMAND_TOPIC}")
    else:
        print(f"[MQTT] Connection failed with code {rc}")
        system_errors_append(f"MQTT connection failed: {rc}")


def on_mqtt_message(client, userdata, msg):
    print(f"[MQTT] Received message on {msg.topic}: {msg.payload.decode()}")
    try:
        command = msg.payload.decode()
        process_mqtt_command(command)
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")
        system_errors_append(f"MQTT message error: {e}")


def process_mqtt_command(command):
    print(f"[MQTT] Processing command: {command}")

    if command == f"initFeeder{FEEDER_NUMBER}":
        print("[MQTT] Initializing feeder...")
        try:
            # Hold _feed_lock for the whole init so we don't collide with
            # IdleTubeDry, manual API actions, or a scheduled feed firing
            # mid-init. SetupSystemBoot doesn't drive the rotor but the
            # subsequent steps do.
            with _feed_lock:
                SetupSystemBoot()
                ReadTempHum()
                HomeRotor()
                MoveToPortOne()
                # Spin the hopper for ~2 s as a sanity check that the screw moves
                # and the opto counts. (Was a bare CountHopperScrew() with no arg.)
                CountHopperScrew(2)
                # Two air pulses — was BlowAir(1, True) / BlowAir(0, False) which
                # passes too many args. BlowAir takes one duration arg.
                BlowAir(1)
                BlowAir(0)
            publish_status(f"sysInitGood{FEEDER_NUMBER}")
        except Exception as e:
            print(f"[MQTT] Initialization error: {e}")
            traceback.print_exc()
            publish_status(f"sysInitExcept{FEEDER_NUMBER}")
            system_errors_append(f"Init error: {e}")

    elif command == f"reqStat{FEEDER_NUMBER}":
        print("[MQTT] Status requested...")
        try:
            ReadTempHum()
            CheckFoodLevel()
            status_msg = (f"status{FEEDER_NUMBER}:"
                          f"food={_round_food_pct(food_percentage)},"
                          f"temp={current_temperature},"
                          f"hum={current_humidity},"
                          f"port={_display_port(current_port)}")
            publish_status(status_msg)
        except Exception as e:
            print(f"[MQTT] Status request error: {e}")
            traceback.print_exc()
            system_errors_append(f"reqStat error: {e}")


def publish_status(message):
    if mqtt_client:
        mqtt_client.publish(MQTT_STATUS_TOPIC, message, qos=MQTT_QOS)
        print(f"[MQTT] Published to {MQTT_STATUS_TOPIC}: {message}")


def setup_mqtt():
    global mqtt_client
    print("[MQTT] Setting up MQTT client...")
    try:
        mqtt_client = mqtt.Client(client_id=f"feeder_{FEEDER_NUMBER}")
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message
        # Auto-reconnect with exponential backoff between 1 and 60 seconds.
        # Without this, the loop_start() worker won't try to reconnect after
        # an unclean broker drop and the feeder silently goes offline.
        mqtt_client.reconnect_delay_set(min_delay=1, max_delay=60)
        mqtt_client.connect(MQTT_BROKER_IP, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print("[MQTT] MQTT client started")
    except Exception as e:
        print(f"[MQTT] Error setting up MQTT: {e}")
        system_errors_append(f"MQTT setup error: {e}")


# ==============================================================================
# HTML TEMPLATES
# ==============================================================================

CSS_STYLES = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f5f7fa;
        color: #333;
        line-height: 1.6;
    }
    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
    header {
        background: linear-gradient(135deg, #2c3e50, #3498db);
        color: white;
        padding: 20px;
        text-align: center;
        margin-bottom: 30px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 { font-size: 1.8em; font-weight: 600; }
    h2 {
        color: #2c3e50;
        margin-bottom: 20px;
        font-size: 1.4em;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
    }
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }
    .info-box {
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        border-left: 4px solid #3498db;
    }
    .info-box label {
        display: block;
        font-size: 0.85em;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }
    .info-box .value { font-size: 1.4em; font-weight: 600; color: #2c3e50; }
    /* v7.7: smaller, lighter line shown directly below the next-feeding
       time. Used by the home page to render the date underneath the
       time in the "Next Scheduled Feeding" tile, matching the upper
       clock layout (time-on-top / date-below). */
    .info-box .value-sub { font-size: 1.0em; font-weight: 400; color: #555; margin-top: 4px; }
    .datetime-display {
        background: white;
        padding: 15px 25px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .datetime-display .time { font-size: 2em; font-weight: 600; color: #2c3e50; }
    .datetime-display .date { font-size: 1em; color: #7f8c8d; }
    .button-group { display: flex; gap: 15px; flex-wrap: wrap; margin-top: 20px; }
    .btn {
        display: inline-block;
        padding: 12px 30px;
        font-size: 1em;
        font-weight: 500;
        text-decoration: none;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .btn-primary { background: #3498db; color: white; }
    .btn-primary:hover {
        background: #2980b9;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(52,152,219,0.3);
    }
    .btn-success { background: #27ae60; color: white; }
    .btn-success:hover {
        background: #219a52;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(39,174,96,0.3);
    }
    .btn-secondary { background: #95a5a6; color: white; }
    .btn-secondary:hover { background: #7f8c8d; }
    .btn-camera { background: #8e44ad; color: white; }
    .btn-camera:hover {
        background: #7d3c98;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(142,68,173,0.3);
    }
    /* v7.3: distinct colour for the Temp Hum log button so it doesn't blend
       in with the blue primary buttons. Dark mustard/amber. */
    .btn-temp { background: #d68910; color: white; }
    .btn-temp:hover {
        background: #b9770e;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(214,137,16,0.3);
    }
    /* v7.4: orange button colour used for Manual Control actions that
       directly affect food/light state (Food Light, Load Food). Brighter
       than btn-temp so the two can sit on the same page without merging. */
    .btn-warning { background: #e67e22; color: white; }
    .btn-warning:hover {
        background: #ca6f1e;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(230,126,34,0.3);
    }
    .form-section {
        background: white;
        padding: 25px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .tank-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 10px;
        margin-bottom: 20px;
    }
    .tank-item {
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding: 8px 12px;
        background: #f8f9fa;
        border-radius: 4px;
    }
    .tank-item-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .tank-item input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; }
    .tank-item select {
        padding: 5px 10px;
        border: 1px solid #ddd;
        border-radius: 4px;
        background: white;
        cursor: pointer;
    }
    .tank-item input[type="text"] {
        width: 100%;
        box-sizing: border-box;
        padding: 5px 8px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 13px;
    }
    .tank-label-readonly {
        font-size: 13px;
        color: #555;
        font-style: italic;
    }
    .config-row {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 15px;
        flex-wrap: wrap;
    }
    .config-row label { min-width: 200px; font-weight: 500; }
    .config-row select,
    .config-row input[type="text"],
    .config-row input[type="number"] {
        padding: 8px 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 1em;
    }
    .config-row input[type="text"],
    .config-row input[type="number"] { width: 150px; }
    .back-link {
        display: inline-block;
        margin-bottom: 20px;
        color: #3498db;
        text-decoration: none;
        font-weight: 500;
    }
    .back-link:hover { text-decoration: underline; }
    /* Camera page specific */
    .camera-wrapper {
        background: white;
        padding: 25px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 20px;
    }
    .camera-feed {
        max-width: 100%;
        border-radius: 6px;
        border: 2px solid #ddd;
        background: #1a1a1a;
    }
    .camera-controls {
        margin-top: 15px;
        display: flex;
        gap: 15px;
        justify-content: center;
        flex-wrap: wrap;
    }
    .camera-status {
        margin-top: 10px;
        font-size: 0.9em;
        color: #7f8c8d;
    }
    .camera-error {
        background: #fdecea;
        color: #c0392b;
        padding: 15px;
        border-radius: 6px;
        margin-top: 15px;
        font-weight: 500;
    }
    /* Food level panel (migrated from v3.4) */
    .food-level-panel {
        background: white; border-radius: 8px; padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        margin-bottom: 20px; border-left: 4px solid #27ae60;
    }
    .food-level-panel h2 { font-size: 1em; color: #7f8c8d; text-transform: uppercase; margin-bottom: 10px; }
    .food-percentage-value { font-size: 2.8em; font-weight: 700; color: #27ae60; }
    .food-percentage-value.low  { color: #e67e22; }
    .food-percentage-value.crit { color: #e74c3c; }
    .food-bar-bg { background: #ecf0f1; border-radius: 6px; height: 18px; margin-top: 10px; overflow: hidden; }
    .food-bar-fill { height: 100%; border-radius: 6px; transition: width 0.5s ease, background 0.5s ease; }
    .food-meta { font-size: 0.78em; color: #95a5a6; margin-top: 6px; }
    .food-error { color: #e74c3c; font-size: 0.85em; margin-top: 6px; }
</style>
"""

CLOCK_SCRIPT = """
<script>
    function updateClock() {
        var now = new Date();
        var hours = now.getHours();
        var ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12;
        var minutes = now.getMinutes().toString().padStart(2, '0');
        var seconds = now.getSeconds().toString().padStart(2, '0');
        document.getElementById('current-time').textContent =
            hours + ':' + minutes + ':' + seconds + ' ' + ampm;
        var d = now.getDate().toString().padStart(2, '0');
        var m = (now.getMonth() + 1).toString().padStart(2, '0');
        document.getElementById('current-date').textContent =
            d + ':' + m + ':' + now.getFullYear();
    }
    setInterval(updateClock, 1000);
    updateClock();
</script>
"""

HOME_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fish Feeding System Hotel {{ hotel_number }}</title>
    {{ css_styles | safe }}
</head>
<body>
    <div class="container">
        <header>
            <h1>Fish Feeding System Hotel {{ hotel_number }} Version 7.7</h1>
        </header>

        <div class="datetime-display">
            <div class="time" id="current-time">--:--:-- --</div>
            <div class="date" id="current-date">--:--:----</div>
        </div>

        <div class="info-grid">
            <div class="info-box">
                <label>Next Scheduled Feeding</label>
                {# v7.7: time-on-top / date-below format matching the
                   upper clock display. The server-side string in
                   next_feeding_time joins the two lines with '\n' for
                   real datetimes, or is a single phrase like
                   "Not scheduled" / "Cycle in progress" with no newline.
                   The JS poller splits on '\n' and updates both spans;
                   on initial render Jinja does the same split here. #}
                {% set _parts = next_feeding.split('\n') %}
                <div class="value" id="home-next-feeding">{{ _parts[0] }}</div>
                <div class="value-sub" id="home-next-feeding-date">{{ _parts[1] if _parts|length > 1 else '' }}</div>
            </div>
            <div class="info-box">
                <label>Air Temperature</label>
                <div class="value"><span id="home-temp">{{ temperature }}</span> C</div>
            </div>
            <div class="info-box">
                <label>Air Humidity</label>
                <div class="value"><span id="home-hum">{{ humidity }}</span> %</div>
            </div>
            <div class="info-box">
                <label>Current Tank Port</label>
                <div class="value" id="home-port">{{ current_port }}</div>
            </div>
            <div class="info-box">
                <label>Fish Food % Left</label>
                <div class="value"><span id="home-food">{{ food_percent }}</span> %</div>
            </div>
        </div>

        <div class="button-group">
            <a href="/config"        class="btn btn-primary">Fish Feeder Configuration</a>
            <a href="/immediate"     class="btn btn-success">Immediate Feed</a>
            <a href="/camera"        class="btn btn-camera">Camera Preview</a>
            <a href="/manual"        class="btn btn-secondary">Manual Control</a>
            <a href="/temp_hum_log"  class="btn btn-temp">Temp Hum log</a>
        </div>

        <div style="margin-top: 25px;">
            <label for="home-log" style="display:block; font-weight:500; margin-bottom:4px;">Activity log:</label>
            <textarea id="home-log" readonly rows="10"
                style="width:100%; box-sizing:border-box; font-family:monospace; font-size:12px;
                       background:#f8f9fa; color:#2c3e50; border:1px solid #ccc; border-radius:4px;
                       padding:6px; resize:vertical;"></textarea>
        </div>
    </div>

    <script>
        // Activity log on the home page mirrors the Manual Control page format,
        // but instead of being driven by user clicks it shows the running
        // backend's event stream — feed cycles, idle dry moves, manual actions,
        // errors, etc. Backend writes to a ring buffer; we poll it every 2 s
        // using a monotonic sequence number so we only fetch what's new.
        var lastEventSeq = 0;

        function logLine(text) {
            var logEl = document.getElementById('home-log');
            if (!logEl) { return; }
            var ts = new Date().toLocaleTimeString();
            logEl.value += '[' + ts + '] ' + text + '\\n';
            logEl.scrollTop = logEl.scrollHeight;
        }

        // Status numbers (temp, humidity, current port, food %, next feeding)
        // — silent updates, no log spam every poll.
        function refreshHomeStatus() {
            fetch('/api/status')
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (d.temperature       !== undefined) { document.getElementById('home-temp').textContent     = (typeof d.temperature === 'number' ? d.temperature.toFixed(1) : d.temperature); }
                    if (d.humidity          !== undefined) { document.getElementById('home-hum').textContent      = (typeof d.humidity    === 'number' ? d.humidity.toFixed(1)    : d.humidity); }
                    if (d.current_port      !== undefined) { document.getElementById('home-port').textContent     = d.current_port; }
                    if (d.food_percentage   !== undefined) { document.getElementById('home-food').textContent     = d.food_percentage; }
                    if (d.next_feeding      !== undefined) {
                        var parts = String(d.next_feeding).split('\\n');
                        document.getElementById('home-next-feeding').textContent      = parts[0];
                        document.getElementById('home-next-feeding-date').textContent = parts.length > 1 ? parts[1] : '';
                    }
                })
                .catch(function () { /* silent — keep showing previous values */ });
        }

        // Event log: pull only events newer than what we've already shown.
        // Each event from the backend already has its own timestamp, so we
        // render them as-is rather than tagging them with the browser clock.
        function fetchRecentEvents() {
            fetch('/api/recent_events?since=' + lastEventSeq)
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (!d.events || d.events.length === 0) { return; }
                    var logEl = document.getElementById('home-log');
                    if (!logEl) { return; }
                    for (var i = 0; i < d.events.length; i++) {
                        var ev = d.events[i];
                        logEl.value += '[' + ev.ts + '] ' + ev.msg + '\\n';
                        if (ev.seq > lastEventSeq) { lastEventSeq = ev.seq; }
                    }
                    logEl.scrollTop = logEl.scrollHeight;
                })
                .catch(function () { /* silent — try again next tick */ });
        }

        logLine('Home page loaded');
        refreshHomeStatus();
        fetchRecentEvents();
        setInterval(refreshHomeStatus, 10000);  // status numbers: every 10 s
        setInterval(fetchRecentEvents, 2000);   // event log: every 2 s for snappy real-time feel
    </script>

    {{ clock_script | safe }}
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Camera page — displays a live MJPEG stream with a snapshot download button
# ---------------------------------------------------------------------------
CAMERA_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Camera Preview - Hotel {{ hotel_number }}</title>
    {{ css_styles | safe }}
</head>
<body>
    <div class="container">
        <header>
            <h1>Camera Preview - Hotel {{ hotel_number }}</h1>
        </header>

        <a href="/" class="back-link">Back to Home</a>

        <!-- Food Level Panel (migrated from v3.4) -->
        <div class="food-level-panel">
            <h2>Food Level (vision analysis)</h2>
            <div id="food-pct-value" class="food-percentage-value">--.-&nbsp;%</div>
            <div class="food-bar-bg">
                <div id="food-bar-fill" class="food-bar-fill"
                     style="width:0%; background:#27ae60;"></div>
            </div>
            <div id="food-meta" class="food-meta">Waiting for first analysis…</div>
            <div id="food-error" class="food-error" style="display:none;"></div>
        </div>

        <div class="camera-wrapper">
            <h2>Live Feed</h2>

            <!--
                The src points to the MJPEG streaming endpoint.
                The browser keeps the connection open and renders each
                incoming JPEG as the frame updates.
            -->
            <img id="camera-feed"
                 class="camera-feed"
                 src="/camera/stream"
                 alt="Camera feed"
                 width="600"
                 height="451"
                 onerror="showCameraError()">

            <div class="camera-status" id="camera-status">
                Receiving live stream at {{ cam_width }}x{{ cam_height }} / {{ cam_fps }} fps
            </div>

            <div id="camera-error" class="camera-error" style="display:none;">
                Camera unavailable. Check that the ribbon cable is seated correctly
                and that the camera interface is enabled in raspi-config.
            </div>

            <div class="camera-controls">
                <a href="/camera/snapshot" class="btn btn-primary" download="snapshot.jpg">
                    Download Snapshot
                </a>
                <button class="btn btn-secondary" onclick="refreshFeed()">
                    Refresh Stream
                </button>
                <button class="btn btn-success" onclick="triggerAnalysis()">
                    Analyse Now
                </button>
            </div>
        </div>
    </div>

    <script>
        function showCameraError() {
            document.getElementById('camera-error').style.display = 'block';
            document.getElementById('camera-status').style.display = 'none';
        }

        function refreshFeed() {
            // Re-attach the stream src to force a reconnect
            var img = document.getElementById('camera-feed');
            img.src = '/camera/stream?' + new Date().getTime();
            document.getElementById('camera-error').style.display = 'none';
            document.getElementById('camera-status').style.display = 'block';
        }

        // --- Food-level polling (migrated from v3.4) ---
        // Colour thresholds for the bar and value text
        const LOW  = 30;   // below this → orange warning
        const CRIT = 10;   // below this → red critical

        function applyColour(pct) {
            const valEl  = document.getElementById('food-pct-value');
            const barEl  = document.getElementById('food-bar-fill');
            let col;
            valEl.classList.remove('low', 'crit');
            if (pct <= CRIT)      { col = '#e74c3c'; valEl.classList.add('crit'); }
            else if (pct <= LOW)  { col = '#e67e22'; valEl.classList.add('low');  }
            else                  { col = '#27ae60'; }
            barEl.style.background = col;
            barEl.style.width      = pct + '%';
        }

        function fetchFoodLevel() {
            fetch('/api/food_level')
                .then(r => r.json())
                .then(data => {
                    const errEl  = document.getElementById('food-error');
                    const metaEl = document.getElementById('food-meta');
                    const valEl  = document.getElementById('food-pct-value');

                    if (data.error) {
                        errEl.textContent = 'Error: ' + data.error;
                        errEl.style.display = 'block';
                        valEl.textContent = '--.- %';
                    } else {
                        errEl.style.display = 'none';
                        const pct = data.percentage;
                        valEl.textContent = pct.toFixed(1) + ' %';
                        applyColour(pct);
                        metaEl.textContent = 'Last analysed: ' + data.timestamp
                            + '  (auto-refresh every {{ analysis_interval }}s)';
                    }
                })
                .catch(() => {
                    document.getElementById('food-error').textContent = 'Could not reach server.';
                    document.getElementById('food-error').style.display = 'block';
                });
        }

        function triggerAnalysis() {
            document.getElementById('food-meta').textContent = 'Analysing…';
            fetch('/api/food_level/trigger', {method: 'POST'})
                .then(() => setTimeout(fetchFoodLevel, 1500));
        }

        // Poll every {{ analysis_interval }} seconds to match the backend schedule
        fetchFoodLevel();
        setInterval(fetchFoodLevel, {{ analysis_interval }} * 1000);
    </script>
</body>
</html>
"""

CONFIG_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fish Feeder Configuration - Hotel {{ hotel_number }}</title>
    {{ css_styles | safe }}
</head>
<body>
    <div class="container">
        <header>
            <h1>Fish Feeder Configuration</h1>
        </header>

        <a href="/" class="back-link">Back to Home</a>

        <form method="POST" action="/config">
            <div class="form-section">
                <h2>Tanks in Use</h2>
                <div class="tank-grid">
                    {% for i in range(1, 61) %}
                    <div class="tank-item">
                        <div class="tank-item-row">
                            <input type="checkbox" name="tank_{{ i }}" id="tank_{{ i }}"
                                   {% if config['TankSettings'].getboolean('tank_' ~ i ~ '_enabled', fallback=False) %}checked{% endif %}>
                            <label for="tank_{{ i }}">Tank {{ i }}</label>
                            <select name="food_{{ i }}">
                                {% for val in range(10, 301, 10) %}
                                <option value="{{ val }}"
                                        {% if config['TankSettings'].get('tank_' ~ i ~ '_food_mg', '50')|int == val %}selected{% endif %}>
                                    {{ val }}
                                </option>
                                {% endfor %}
                            </select>
                            <span>mg</span>
                        </div>
                        <input type="text" name="label_{{ i }}" id="label_{{ i }}"
                               maxlength="40" placeholder="(optional label)"
                               value="{{ config['TankSettings'].get('tank_' ~ i ~ '_label', '') }}">
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="form-section">
                <h2>Feed Schedule Settings</h2>
                {# v7.2: "Feeds per 24 hours" select removed. Feed timing
                   is now driven by the 10 fixed-time slots on the new
                   "Feeding times per 24 hour" page. #}
                <div class="config-row">
                    <label>
                        <input type="checkbox" name="rotor_wiggle"
                               {% if config['FeedSchedule'].getboolean('rotor_wiggle_enabled', fallback=False) %}checked{% endif %}>
                        Rotor Wiggle
                    </label>
                    <label for="wiggle_number">Wiggle Number:</label>
                    <select name="wiggle_number" id="wiggle_number">
                        {% for val in range(0, 5) %}
                        <option value="{{ val }}"
                                {% if config['FeedSchedule'].get('wiggle_number', '0')|int == val %}selected{% endif %}>
                            {{ val }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="config-row">
                    <label for="main_air_pulse">Main Air Pulse Time:</label>
                    <select name="main_air_pulse" id="main_air_pulse">
                        {% for val in range(1, 11) %}
                        <option value="{{ val }}"
                                {% if config['FeedSchedule'].get('main_air_pulse_time', '5')|int == val %}selected{% endif %}>
                            {{ val }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="config-row">
                    <label for="wiggle_air_pulse">Wiggle Air Pulse Time:</label>
                    <select name="wiggle_air_pulse" id="wiggle_air_pulse">
                        {% for val in ['1.0', '1.5', '2.0', '2.5', '3.0'] %}
                        <option value="{{ val }}"
                                {% if config['FeedSchedule'].get('wiggle_air_pulse_time', '1.0') == val %}selected{% endif %}>
                            {{ val }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="config-row">
                    <label for="pre_food_air_dry">Pre-food air dry time:</label>
                    <select name="pre_food_air_dry" id="pre_food_air_dry">
                        {% for val in range(5, 61, 5) %}
                        <option value="{{ val }}"
                                {% if config['FeedSchedule'].get('pre_food_air_dry_time', '5')|int == val %}selected{% endif %}>
                            {{ val }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="config-row">
                    <label>
                        <input type="checkbox" name="dry_enabled"
                               {% if config['FeedSchedule'].getboolean('dry_enabled', fallback=False) %}checked{% endif %}>
                        Tube dry
                    </label>
                    <label>
                        <input type="checkbox" name="dry_active_only"
                               {% if config['FeedSchedule'].getboolean('dry_active_only', fallback=False) %}checked{% endif %}>
                        Only dry active tubes
                    </label>
                    <label for="tube_dry_time">Tube dry time (mins):</label>
                    <input type="number" name="tube_dry_time" id="tube_dry_time"
                           min="1" max="30"
                           value="{{ config['FeedSchedule'].get('tube_dry_time', '5') }}">
                </div>
            </div>

            <div class="button-group">
                <button type="submit" class="btn btn-primary">Save Configuration</button>
                <a href="/feed_times" class="btn btn-primary">Feeding times per 24 hour</a>
            </div>
        </form>
    </div>
{# v7.3: "Home Rotor" button removed from the Configuration page (and its
   companion homeRotor() JS handler with it). Home Rotor remains available
   on the Manual Control page where it logically belongs. #}
</body>
</html>
"""

# v7.2: page where the user sets the up-to-10 fixed-time feeding slots that
# CheckFeedTiming reads. Each slot has an enable checkbox, an hour dropdown
# (00..23), and a minute dropdown in 15-minute increments. Both posted back
# as feed_<n>_enabled and feed_<n>_time ("HH:MM") in [FeedSchedule].
FEED_TIMES_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feeding times per 24 hour - Hotel {{ hotel_number }}</title>
    {{ css_styles | safe }}
</head>
<body>
    <div class="container">
        <header>
            <h1>Feeding times per 24 hour</h1>
        </header>

        <a href="/config" class="back-link">Back to Configuration</a>

        <form method="POST" action="/feed_times">
            <div class="form-section">
                <h2>Daily feed slots</h2>
                <p style="color:#555; font-size:14px;">
                    Enable up to ten fixed times of day at which the feeder
                    will run. Times are local-clock and use 15-minute steps.
                    A slot whose moment passes while the system is offline
                    is skipped (issue an immediate feed if needed).
                </p>

                {% for i in range(1, 11) %}
                {% set _t = config['FeedSchedule'].get('feed_' ~ i ~ '_time', '00:00') %}
                {% set _parts = _t.split(':') %}
                {% set _h = _parts[0]|int if _parts|length == 2 else 0 %}
                {% set _m = _parts[1]|int if _parts|length == 2 else 0 %}
                <div class="config-row">
                    <label style="min-width:90px;">
                        <input type="checkbox" name="feed_{{ i }}_enabled"
                               {% if config['FeedSchedule'].getboolean('feed_' ~ i ~ '_enabled', fallback=False) %}checked{% endif %}>
                        Feed {{ i }}
                    </label>
                    <label for="feed_{{ i }}_hour">Time:</label>
                    <select name="feed_{{ i }}_hour" id="feed_{{ i }}_hour">
                        {% for hv in range(0, 24) %}
                        <option value="{{ '%02d'|format(hv) }}" {% if hv == _h %}selected{% endif %}>
                            {{ '%02d'|format(hv) }}
                        </option>
                        {% endfor %}
                    </select>
                    <span>:</span>
                    <select name="feed_{{ i }}_minute" id="feed_{{ i }}_minute">
                        {% for mv in [0, 15, 30, 45] %}
                        <option value="{{ '%02d'|format(mv) }}" {% if mv == _m %}selected{% endif %}>
                            {{ '%02d'|format(mv) }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                {% endfor %}
            </div>

            <div class="button-group">
                <button type="submit" class="btn btn-primary">Save Feeding Times</button>
                <a href="/config" class="btn btn-secondary">Back to Configuration</a>
            </div>
        </form>
    </div>
</body>
</html>
"""

IMMEDIATE_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Immediate Feed - Hotel {{ hotel_number }}</title>
    {{ css_styles | safe }}
</head>
<body>
    <div class="container">
        <header>
            <h1>Immediate Feed</h1>
        </header>

        <a href="/" class="back-link">Back to Home</a>

        <form method="POST" action="/immediate">
            <div class="form-section">
                <h2>Tanks to Feed</h2>
                <div class="tank-grid">
                    {% for i in range(1, 61) %}
                    <div class="tank-item">
                        <div class="tank-item-row">
                            <input type="checkbox" name="imm_tank_{{ i }}" id="imm_tank_{{ i }}"
                                   {% if config['ImmediateFeed'].getboolean('tank_' ~ i ~ '_enabled', fallback=False) %}checked{% endif %}>
                            <label for="imm_tank_{{ i }}">Tank {{ i }}</label>
                            <select name="imm_food_{{ i }}">
                                {% for val in range(10, 301, 10) %}
                                <option value="{{ val }}"
                                        {% if config['ImmediateFeed'].get('tank_' ~ i ~ '_food_mg', '50')|int == val %}selected{% endif %}>
                                    {{ val }}
                                </option>
                                {% endfor %}
                            </select>
                            <span>mg</span>
                        </div>
                        {# Per-tank label, read-only here — owned and edited
                           by the Fish Feeder Configuration page. Sourced from
                           TankSettings (single source of truth) so a label
                           change on the Configuration page shows up here on
                           the next reload without further action. v7.6:
                           always render the label slot (was conditionally
                           hidden when blank) — empty labels now show "N/A"
                           so the user can see at a glance which tanks
                           haven't been named. #}
                        {% set _tank_label = config['TankSettings'].get('tank_' ~ i ~ '_label', '') %}
                        <span class="tank-label-readonly">{{ _tank_label if _tank_label else 'N/A' }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>

            {# v7.5: "Feed Options" section removed — held two checkboxes
               ("Regular Feed Schedule", "Delay Feed by Normal Amount")
               that were never wired to any behaviour. #}

            <div class="button-group">
                <button type="submit" class="btn btn-success">Start Feeding Now</button>
            </div>
        </form>
    </div>
</body>
</html>
"""


TEMP_HUM_LOG_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Temp / Humidity Log</title>
    {{ css_styles | safe }}
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>Temperature &amp; Humidity (last 24 h)</h1>

        <div class="form-section">
            <div id="log-status" class="camera-status">Loading…</div>
            <canvas id="th-chart" height="120"></canvas>
        </div>

        <div class="button-group">
            <a href="/" class="btn btn-secondary">&larr; Home</a>
        </div>
    </div>

    <script>
        let chart = null;

        function buildChart(labels, temps, hums) {
            const ctx = document.getElementById('th-chart').getContext('2d');
            if (chart) { chart.destroy(); }
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Temperature (°C)',
                            data: temps,
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231,76,60,0.15)',
                            yAxisID: 'yT',
                            tension: 0.25,
                            spanGaps: true
                        },
                        {
                            label: 'Humidity (%)',
                            data: hums,
                            borderColor: '#2980b9',
                            backgroundColor: 'rgba(41,128,185,0.15)',
                            yAxisID: 'yH',
                            tension: 0.25,
                            spanGaps: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        yT: {
                            type: 'linear', position: 'left',
                            title: { display: true, text: 'Temperature (°C)' }
                        },
                        yH: {
                            type: 'linear', position: 'right',
                            title: { display: true, text: 'Humidity (%)' },
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        }

        function loadLog() {
            const statusEl = document.getElementById('log-status');
            fetch('/api/temp_hum_log')
                .then(r => r.json())
                .then(d => {
                    const rows = d.rows || [];
                    const labels = rows.map(r => r.ts);
                    const temps  = rows.map(r => r.temp);
                    const hums   = rows.map(r => r.hum);
                    statusEl.textContent = rows.length + ' sample(s) plotted (last 24 h).';
                    buildChart(labels, temps, hums);
                })
                .catch(err => {
                    statusEl.textContent = 'Failed to load log: ' + err;
                });
        }
        loadLog();
        // Refresh every 5 minutes so the page stays current if left open.
        setInterval(loadLog, 5 * 60 * 1000);
    </script>
</body>
</html>
"""


MANUAL_CONTROL_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manual Control - Hotel {{ hotel_number }}</title>
    {{ css_styles | safe }}
</head>
<body>
    <div class="container">
        <header>
            <h1>Manual Control - Hotel {{ hotel_number }}</h1>
        </header>

        <a href="/" class="back-link">Back to Home</a>

        <div class="form-section">
            <h2>Manual Control</h2>

            <div class="config-row">
                <label>Home status:</label>
                <span><strong id="home-status-value">{{ home_status }}</strong></span>
            </div>
            <div class="config-row">
                <label>Current port:</label>
                <span><strong id="current-port-value">{{ current_port_value }}</strong></span>
            </div>
            <div class="config-row">
                <label>Food light:</label>
                <span><strong id="food-light-value">{{ food_light_status }}</strong></span>
            </div>
            <div class="config-row">
                <label>Hopper Clogged:</label>
                <span><strong id="hopper-clog-value">{{ hopper_clog_status }}</strong></span>
            </div>
            <div class="config-row">
                <label>+24 volts ok:</label>
                <span><strong id="power-ok-value">{{ power_ok_status }}</strong></span>
            </div>

            <div id="manual-status" class="camera-status">Ready.</div>

            <div style="margin-top: 10px;">
                <label for="manual-log" style="display:block; font-weight:500; margin-bottom:4px;">Activity log:</label>
                <textarea id="manual-log" readonly rows="10"
                    style="width:100%; box-sizing:border-box; font-family:monospace; font-size:12px;
                           background:#f8f9fa; color:#2c3e50; border:1px solid #ccc; border-radius:4px;
                           padding:6px; resize:vertical;"></textarea>
            </div>

            <div class="button-group">
                <button type="button" class="btn btn-success"
                        onclick="manualAction('/api/home_rotor', 'Home Rotor')">
                    Home Rotor
                </button>
                <button type="button" class="btn btn-success"
                        onclick="manualAction('/api/move_to_port_one', 'Move to Port One')">
                    Move to Port One
                </button>
                <button type="button" class="btn btn-secondary"
                        onclick="manualAction('/api/setup_allmotion', 'Setup allmotion')">
                    Setup allmotion
                </button>
                <button type="button" class="btn btn-success"
                        onclick="manualAction('/api/check_food_level', 'Check food level')">
                    Check food level
                </button>
                <button type="button" class="btn btn-warning"
                        onclick="manualAction('/api/food_light', 'Food Light')">
                    Food Light
                </button>
                <button type="button" class="btn btn-success"
                        onclick="manualAction('/api/check_clog', 'Check Clog')">
                    Check Clog
                </button>
                <button type="button" class="btn btn-success"
                        onclick="manualAction('/api/check_power', 'Check Power')">
                    Check Power
                </button>
                <button type="button" class="btn btn-success"
                        onclick="manualAction('/api/slack_test', 'Slack test')">
                    Slack test
                </button>
            </div>

            <div style="margin-top: 25px;">
                <div class="config-row">
                    <label>Move ports (1-60):</label>
                    <input type="number" id="move_ports_value" min="1" max="60" value="1">
                    <button type="button" class="btn btn-success"
                            onclick="manualActionWithValue('/api/move_ports', 'Move ports', 'move_ports_value', 1, 60)">
                        Move ports
                    </button>
                </div>
                <div class="config-row">
                    <label>Blow Air (1-20):</label>
                    <input type="number" id="blow_air_value" min="1" max="20" value="1">
                    <button type="button" class="btn btn-success"
                            onclick="manualActionWithValue('/api/blow_air', 'Blow Air', 'blow_air_value', 1, 20)">
                        Blow Air
                    </button>
                </div>
                <div class="config-row">
                    <label>Clean Rotor (1-5):</label>
                    <input type="number" id="clean_rotor_value" min="1" max="5" value="1">
                    <button type="button" class="btn btn-success"
                            onclick="manualActionWithValue('/api/clean_rotor', 'Clean Rotor', 'clean_rotor_value', 1, 5)">
                        Clean Rotor
                    </button>
                </div>
                <div class="config-row">
                    <label>Load Food (10-1000 mg):</label>
                    <input type="number" id="load_food_value" min="10" max="1000" value="10">
                    <button type="button" class="btn btn-warning"
                            onclick="manualActionWithValue('/api/load_food', 'Load Food', 'load_food_value', 10, 1000)">
                        Load Food
                    </button>
                </div>
                <div class="config-row">
                    <label>Settle motor (1-20):</label>
                    <input type="number" id="settle_motor_value" min="1" max="20" value="1">
                    <button type="button" class="btn btn-success"
                            onclick="manualActionWithValue('/api/settle_motor', 'Settle motor', 'settle_motor_value', 1, 20)">
                        Settle motor
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function logLine(text) {
            var logEl = document.getElementById('manual-log');
            var ts = new Date().toLocaleTimeString();
            logEl.value += '[' + ts + '] ' + text + '\\n';
            logEl.scrollTop = logEl.scrollHeight;
        }

        function refreshStatus() {
            fetch('/api/manual_status', { method: 'GET' })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    document.getElementById('home-status-value').textContent = data.home_status;
                    document.getElementById('current-port-value').textContent = data.current_port_value;
                    document.getElementById('food-light-value').textContent = data.food_light_status;
                    document.getElementById('hopper-clog-value').textContent = data.hopper_clog_status;
                    document.getElementById('power-ok-value').textContent = data.power_ok_status;
                    logLine('Status refreshed');
                })
                .catch(function (err) { logLine('Status refresh failed: ' + err); });
        }

        function showResult(statusEl, label, status, text) {
            var msg;
            try {
                var data = JSON.parse(text);
                msg = data.message || data.status || 'done';
            } catch (e) {
                var snippet = text ? text.substring(0, 300) : '(empty body)';
                msg = 'HTTP ' + status + ' non-JSON response: ' + snippet;
            }
            statusEl.textContent = label + ': ' + msg;
        }

        function manualAction(endpoint, label) {
            var statusEl = document.getElementById('manual-status');
            statusEl.textContent = label + ': running...';
            logLine(label + ': click registered, sending to ' + endpoint);
            fetch(endpoint, { method: 'POST' })
                .then(function (response) {
                    return response.text().then(function (text) {
                        showResult(statusEl, label, response.status, text);
                        logLine(label + ': server responded (HTTP ' + response.status + ')');
                        refreshStatus();
                    });
                })
                .catch(function (err) {
                    statusEl.textContent = label + ': network error - ' + err;
                    logLine(label + ': network error - ' + err);
                });
        }

        function manualActionWithValue(endpoint, label, inputId, minVal, maxVal) {
            var statusEl = document.getElementById('manual-status');
            var raw = document.getElementById(inputId).value;
            var val = parseInt(raw, 10);
            if (isNaN(val) || val < minVal || val > maxVal) {
                statusEl.textContent = label + ': value must be an integer between ' + minVal + ' and ' + maxVal;
                logLine(label + ': invalid value (' + raw + '), must be ' + minVal + '-' + maxVal);
                return;
            }
            var labelWithVal = label + ' (' + val + ')';
            statusEl.textContent = labelWithVal + ': running...';
            logLine(labelWithVal + ': click registered, sending to ' + endpoint);
            fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: val })
            })
                .then(function (response) {
                    return response.text().then(function (text) {
                        showResult(statusEl, labelWithVal, response.status, text);
                        logLine(labelWithVal + ': server responded (HTTP ' + response.status + ')');
                        refreshStatus();
                    });
                })
                .catch(function (err) {
                    statusEl.textContent = labelWithVal + ': network error - ' + err;
                    logLine(labelWithVal + ': network error - ' + err);
                });
        }
    </script>
</body>
</html>
"""


# ==============================================================================
# FLASK ROUTES
# ==============================================================================

@app.route('/')
def home():
    print("[WEB] Home page requested")
    ReadTempHum()
    return render_template_string(
        HOME_PAGE_TEMPLATE,
        hotel_number=HOTEL_NUMBER,
        next_feeding=next_feeding_time,
        temperature=f"{current_temperature:.1f}",
        humidity=f"{current_humidity:.1f}",
        current_port=_display_port(current_port),
        food_percent=_round_food_pct(food_percentage),
        css_styles=CSS_STYLES,
        clock_script=CLOCK_SCRIPT
    )


@app.route('/camera')
def camera_page():
    """
    Renders the camera preview page.

    Inputs: None
    Outputs: Rendered HTML template containing the live MJPEG stream
    """
    print("[WEB] Camera page requested")
    return render_template_string(
        CAMERA_PAGE_TEMPLATE,
        hotel_number=HOTEL_NUMBER,
        css_styles=CSS_STYLES,
        cam_width=CAMERA_STREAM_WIDTH,
        cam_height=CAMERA_STREAM_HEIGHT,
        cam_fps=CAMERA_FRAMERATE,
        analysis_interval=FOOD_ANALYSIS_INTERVAL
    )


@app.route('/camera/stream')
def camera_stream():
    """
    MJPEG streaming endpoint.
    Streams frames from the Pi camera as a multipart HTTP response.
    The browser's <img> tag keeps the connection open and refreshes
    each frame automatically — no JavaScript polling required.

    Inputs: None
    Outputs: Flask Response with MJPEG multipart content
    """
    print("[WEB] Camera stream requested")
    return Response(
        generate_mjpeg_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/camera/snapshot')
def camera_snapshot():
    """
    Returns a single JPEG snapshot for download.

    Inputs: None
    Outputs: Flask Response with a JPEG image, or 503 if camera unavailable
    """
    print("[WEB] Camera snapshot requested")
    jpeg_bytes = capture_snapshot()
    if jpeg_bytes is None:
        return "Camera unavailable", 503
    return Response(jpeg_bytes, mimetype='image/jpeg')


# ------------------------------------------------------------------------------
# Food level API endpoints (migrated from v3.4)
# ------------------------------------------------------------------------------

@app.route('/api/food_level')
def api_food_level():
    """Return the most recent food-level analysis result as JSON."""
    with _food_analysis_lock:
        result = dict(_last_food_analysis_result)
    return jsonify(result)


@app.route('/api/food_level/trigger', methods=['POST'])
def api_food_level_trigger():
    """Immediately trigger a fresh food-level analysis in a background thread."""
    t = threading.Thread(target=_run_food_analysis_from_camera, daemon=True)
    t.start()
    return jsonify({"status": "triggered"})


@app.route('/config', methods=['GET', 'POST'])
def config_page():
    config = load_config()

    if request.method == 'POST':
        print("[WEB] Configuration form submitted")
        for i in range(1, 61):
            config['TankSettings'][f'tank_{i}_enabled'] = str(f'tank_{i}' in request.form).lower()
            config['TankSettings'][f'tank_{i}_food_mg'] = request.form.get(f'food_{i}', '50')
            # Free-text per-tank label. Strip leading/trailing whitespace and
            # cap at 40 chars on the server side too — the input has maxlength
            # but a manually crafted POST could bypass it.
            label = request.form.get(f'label_{i}', '').strip()[:40]
            config['TankSettings'][f'tank_{i}_label'] = label

        # v7.2: "feeds_per_24_hours" form field removed (the legacy
        # interval scheduler was replaced by fixed-time slots on the new
        # "Feeding times per 24 hour" page). The key remains in the .ini
        # for backward-compat with older configs but is no longer written
        # by this handler.
        config['FeedSchedule']['rotor_wiggle_enabled'] = str('rotor_wiggle' in request.form).lower()
        config['FeedSchedule']['wiggle_number']        = request.form.get('wiggle_number', '0')
        config['FeedSchedule']['main_air_pulse_time']  = request.form.get('main_air_pulse', '5')
        config['FeedSchedule']['wiggle_air_pulse_time']= request.form.get('wiggle_air_pulse', '1.0')
        config['FeedSchedule']['pre_food_air_dry_time']= request.form.get('pre_food_air_dry', '5')
        # Clamp tube_dry_time to its valid range (1..30 minutes) so a tampered
        # form submit can't store nonsense.
        try:
            tdt = int(request.form.get('tube_dry_time', '5'))
        except ValueError:
            tdt = 5
        tdt = max(1, min(30, tdt))
        config['FeedSchedule']['tube_dry_time'] = str(tdt)
        # Mirror to the module-level variable so subsequent code uses the
        # latest value without having to re-read the .ini.
        global tube_dry_time
        tube_dry_time = tdt

        # Tube-dry enable checkbox — present in form means True, absent means False.
        config['FeedSchedule']['dry_enabled'] = str('dry_enabled' in request.form).lower()
        global dry_enabled
        dry_enabled = ('dry_enabled' in request.form)

        # "Only dry active tubes" checkbox — when True, IdleTubeDry walks
        # only the enabled-tank ports rather than every port 1..60.
        config['FeedSchedule']['dry_active_only'] = str('dry_active_only' in request.form).lower()
        global dry_active_only
        dry_active_only = ('dry_active_only' in request.form)

        save_config(config)
        # Update the home page's "Next Scheduled Feeding" display immediately
        # rather than waiting for CheckFeedTiming's next 60-second tick.
        _refresh_next_feeding_time()
        print("[WEB] Configuration saved")
        return redirect(url_for('config_page'))

    print("[WEB] Configuration page requested")
    return render_template_string(
        CONFIG_PAGE_TEMPLATE,
        hotel_number=HOTEL_NUMBER,
        config=config,
        css_styles=CSS_STYLES
    )


@app.route('/feed_times', methods=['GET', 'POST'])
def feed_times_page():
    """Page for the 10 daily feeding-time slots. GET renders the form
    pre-filled from FeedSchedule; POST persists the new values and
    redirects back to itself so the user sees the saved state.
    """
    config = load_config()

    if request.method == 'POST':
        print("[WEB] Feed times form submitted")
        for i in range(1, 11):
            enabled = f'feed_{i}_enabled' in request.form
            hour_str   = request.form.get(f'feed_{i}_hour',   '00')
            minute_str = request.form.get(f'feed_{i}_minute', '00')
            # Clamp defensively in case a tampered submit slips bad values
            # past the browser-side dropdowns.
            try:
                h = max(0, min(23, int(hour_str)))
                m_raw = int(minute_str)
                # Snap to 15-min grid; reject anything else by rounding down.
                m = (m_raw // 15) * 15 if 0 <= m_raw <= 59 else 0
            except (TypeError, ValueError):
                h, m = 0, 0
            config['FeedSchedule'][f'feed_{i}_enabled'] = str(enabled).lower()
            config['FeedSchedule'][f'feed_{i}_time']    = f"{h:02d}:{m:02d}"

        save_config(config)
        # Refresh the home-page "Next Scheduled Feeding" display immediately
        # so the user sees their new schedule reflected on the home page
        # without waiting for CheckFeedTiming's next tick.
        _refresh_next_feeding_time()
        print("[WEB] Feed times saved")
        return redirect(url_for('feed_times_page'))

    print("[WEB] Feed times page requested")
    return render_template_string(
        FEED_TIMES_PAGE_TEMPLATE,
        hotel_number=HOTEL_NUMBER,
        config=config,
        css_styles=CSS_STYLES,
    )


@app.route('/immediate', methods=['GET', 'POST'])
def immediate_page():
    config = load_config()

    if request.method == 'POST':
        print("[WEB] Immediate feed form submitted")
        tank_checkboxes = []
        tank_food_amounts = []

        for i in range(1, 61):
            tank_checkboxes.append(f'imm_tank_{i}' in request.form)
            tank_food_amounts.append(int(request.form.get(f'imm_food_{i}', '50')))
            config['ImmediateFeed'][f'tank_{i}_enabled'] = str(f'imm_tank_{i}' in request.form).lower()
            config['ImmediateFeed'][f'tank_{i}_food_mg'] = request.form.get(f'imm_food_{i}', '50')

        # v7.5: regular_schedule + delay_feed reads removed — both
        # checkboxes were retired from the form along with their unused
        # backend logic.

        save_config(config)
        immediateFoodNow(tank_checkboxes, tank_food_amounts)
        return redirect(url_for('home'))

    print("[WEB] Immediate feed page requested")
    return render_template_string(
        IMMEDIATE_PAGE_TEMPLATE,
        hotel_number=HOTEL_NUMBER,
        config=config,
        css_styles=CSS_STYLES
    )


# ------------------------------------------------------------------------------
# Hardware-action helpers
#
# All "perform a hardware action and report success/failure" API routes
# share the same try/except + JSON response shape. The decorator below
# captures that pattern in one place. The validate helper does the same
# for "extract an int from {value:N} and bounds-check it".
# ------------------------------------------------------------------------------

def hw_action(label, use_feed_lock=True):
    """Decorator: wrap a Flask view function so any unhandled exception is
    converted to a 500 JSON response with traceback printed to stdout.

    use_feed_lock: when True (default), the wrapped function holds the shared
    _feed_lock for its entire duration so it can't issue serial commands at
    the same time as RunFoodSequence or IdleTubeDry. Set False for routes
    that don't touch hardware (e.g. slack_test) so they don't queue behind
    a long-running feed cycle.
    """
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_event(f"Manual action: {label}")
            if use_feed_lock:
                # Bounded wait — refuse the request rather than hang forever
                # if a feed cycle is in progress. 60 s is generous for the
                # operator clicking a manual button while a cycle is mid-pour.
                got = _feed_lock.acquire(timeout=60)
                if not got:
                    return jsonify({
                        'status': 'error',
                        'message': f'{label} timed out waiting for hardware lock '
                                   '(feed/dry cycle in progress)'
                    }), 503
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    traceback.print_exc()
                    return jsonify({
                        'status': 'error',
                        'message': f'{label} failed: {type(e).__name__}: {e}'
                    }), 500
                finally:
                    _feed_lock.release()
            else:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    traceback.print_exc()
                    return jsonify({
                        'status': 'error',
                        'message': f'{label} failed: {type(e).__name__}: {e}'
                    }), 500
        return wrapper
    return deco


def _validate_int(data, label, lo, hi):
    """Pull 'value' from the JSON body, validate as int in [lo, hi].

    Returns (int, None) on success, (None, flask_response_tuple) on failure.
    The response tuple is a Flask (jsonify, 400) ready to be returned.
    """
    try:
        v = int(data.get('value'))
    except (TypeError, ValueError):
        return None, (jsonify({'status': 'error', 'message': f'Invalid {label}'}), 400)
    if v < lo or v > hi:
        return None, (jsonify({
            'status': 'error',
            'message': f'{label} must be between {lo} and {hi}'
        }), 400)
    return v, None


@app.route('/api/home_rotor', methods=['POST'])
@hw_action('HomeRotor')
def api_home_rotor():
    print("[API] Home rotor requested")
    HomeRotor()
    return jsonify({'status': 'success', 'message': 'Rotor homing initiated'})


@app.route('/manual')
def manual_page():
    print("[WEB] Manual control page requested")
    return render_template_string(
        MANUAL_CONTROL_PAGE_TEMPLATE,
        hotel_number=HOTEL_NUMBER,
        css_styles=CSS_STYLES,
        home_status=("HOME" if current_port == 100 else "NOT HOME"),
        current_port_value=_display_port(current_port),
        food_light_status=("ON" if food_light_state else "OFF"),
        hopper_clog_status=("Clogged" if GPIO.input(4) else "No Clog"),
        power_ok_status=("OK" if GPIO.input(17) else "Power Failed")
    )


@app.route('/temp_hum_log')
def temp_hum_log_page():
    print("[WEB] Temp/Hum log page requested")
    return render_template_string(
        TEMP_HUM_LOG_PAGE_TEMPLATE,
        css_styles=CSS_STYLES
    )


def _build_default_temp_hum_rows():
    """Generate TEMP_HUM_PLOT_POINTS rows of default values, timestamps
    spaced one hour apart ending at "now". Used by the API as a fallback
    so the plot is always populated even if the logger thread hasn't
    written its first file yet (or the file got removed).
    """
    now = datetime.now()
    rows = []
    for i in range(TEMP_HUM_PLOT_POINTS):
        ts = now - timedelta(hours=(TEMP_HUM_PLOT_POINTS - 1 - i))
        rows.append({
            "ts":   ts.strftime("%Y-%m-%d %H:%M:%S"),
            "temp": TEMP_HUM_DEFAULT_TEMP,
            "hum":  TEMP_HUM_DEFAULT_HUM,
        })
    return rows


@app.route('/api/temp_hum_log', methods=['GET'])
def api_temp_hum_log():
    rows = _read_temp_hum_log()
    if not rows:
        # Logger hasn't seeded yet, or file was deleted — return defaults so
        # the page always has something to plot.
        rows = _build_default_temp_hum_rows()
    else:
        # The on-disk log keeps 5 days; the page only shows the most recent 24 h.
        rows = rows[-TEMP_HUM_PLOT_POINTS:]
    return jsonify({'rows': rows})


@app.route('/api/manual_status', methods=['GET'])
def api_manual_status():
    return jsonify({
        'home_status':        ("HOME" if current_port == 100 else "NOT HOME"),
        'current_port_value': _display_port(current_port),
        'food_light_status':  ("ON" if food_light_state else "OFF"),
        'hopper_clog_status': ("Clogged" if GPIO.input(4) else "No Clog"),
        'power_ok_status':    ("OK" if GPIO.input(17) else "Power Failed")
    })


@app.route('/api/move_to_port_one', methods=['POST'])
@hw_action('MoveToPortOne')
def api_move_to_port_one():
    print("[API] Move to Port One requested")
    MoveToPortOne()
    return jsonify({'status': 'success', 'message': 'Move to Port One initiated'})


@app.route('/api/setup_allmotion', methods=['POST'])
@hw_action('SetupSystemBoot')
def api_setup_allmotion():
    print("[API] Setup allmotion requested")
    SetupSystemBoot()
    return jsonify({'status': 'success', 'message': 'Setup allmotion completed'})


@app.route('/api/check_food_level', methods=['POST'])
@hw_action('CheckFoodLevel')
def api_check_food_level():
    print("[API] Check food level requested")
    CheckFoodLevel()
    return jsonify({'status': 'success', 'message': 'Check food level completed'})


@app.route('/api/check_clog', methods=['POST'])
@hw_action('CheckClogs', use_feed_lock=False)
def api_check_clog():
    print("[API] Check Clog requested")
    state = CheckClogs()
    label = "Clogged" if state else "No Clog"
    return jsonify({'status': 'success', 'message': f'Hopper status: {label}'})


@app.route('/api/check_power', methods=['POST'])
@hw_action('CheckPower', use_feed_lock=False)
def api_check_power():
    print("[API] Check Power requested")
    state = CheckPower()
    label = "OK" if state else "Power Failed"
    return jsonify({'status': 'success', 'message': f'+24 V status: {label}'})


@app.route('/api/settle_motor', methods=['POST'])
@hw_action('SettleMotor')
def api_settle_motor():
    data = request.get_json(silent=True) or {}
    settle_time, err = _validate_int(data, 'settle time', 1, 20)
    if err: return err
    print(f"[API] Settle motor requested: settle_time={settle_time}")
    SettleMotor(settle_time)
    return jsonify({'status': 'success', 'message': f'Settle motor for {settle_time} completed'})


@app.route('/api/food_light', methods=['POST'])
def api_food_light():
    # Not using hw_action because we need bespoke rollback logic on failure.
    global food_light_state
    food_light_state = not food_light_state
    new_state = food_light_state
    print(f"[API] Food Light toggle requested (new state: {'ON' if new_state else 'OFF'})")
    try:
        LightTube(new_state)
    except Exception as e:
        traceback.print_exc()
        # Roll back the state toggle on failure so the next click retries the same transition
        food_light_state = not food_light_state
        return jsonify({'status': 'error', 'message': f'LightTube failed: {type(e).__name__}: {e}'}), 500
    return jsonify({'status': 'success', 'message': f"Food Light {'ON' if new_state else 'OFF'}"})


@app.route('/api/move_ports', methods=['POST'])
@hw_action('MovePorts')
def api_move_ports():
    data = request.get_json(silent=True) or {}
    # User-facing range: 1..60 ports forward (1 = step to next port,
    # 60 = full revolution back to current). Aligned with the Manual
    # Control page input min=1 max=60.
    port_number, err = _validate_int(data, 'port number', 1, 60)
    if err: return err
    print(f"[API] Move ports requested: port_number={port_number}")
    MovePorts(port_number)
    return jsonify({'status': 'success', 'message': f'Move ports to {port_number} completed'})


@app.route('/api/blow_air', methods=['POST'])
@hw_action('BlowAir')
def api_blow_air():
    data = request.get_json(silent=True) or {}
    duration, err = _validate_int(data, 'duration', 1, 20)
    if err: return err
    print(f"[API] Blow Air requested: duration={duration}")
    BlowAir(duration)
    return jsonify({'status': 'success', 'message': f'Blow Air for {duration} completed'})


@app.route('/api/clean_rotor', methods=['POST'])
@hw_action('CleanRotor')
def api_clean_rotor():
    data = request.get_json(silent=True) or {}
    clean_cycles, err = _validate_int(data, 'cycle count', 1, 5)
    if err: return err
    print(f"[API] Clean Rotor requested: clean_cycles={clean_cycles}")
    CleanRotor(clean_cycles)
    return jsonify({'status': 'success', 'message': f'Clean Rotor for {clean_cycles} cycles completed'})


@app.route('/api/load_food', methods=['POST'])
@hw_action('LoadFood')
def api_load_food():
    data = request.get_json(silent=True) or {}
    amount, err = _validate_int(data, 'amount', 10, 1000)
    if err: return err
    print(f"[API] Load Food requested: amount={amount}")
    LoadFood(amount)
    return jsonify({'status': 'success', 'message': f'Load Food {amount} mg completed'})


@app.route('/api/slack_test', methods=['POST'])
@hw_action('Slack test', use_feed_lock=False)
def api_slack_test():
    print("[API] Slack test requested")
    send_slack_notification("Testing the messaging from feeder 1")
    return jsonify({'status': 'success', 'message': 'Slack test message sent'})


@app.route('/api/status', methods=['GET'])
def api_status():
    print("[API] Status requested")
    ReadTempHum()
    return jsonify({
        'feeder_number':  FEEDER_NUMBER,
        'temperature':    current_temperature,
        'humidity':       current_humidity,
        'current_port':   _display_port(current_port),
        'food_percentage':_round_food_pct(food_percentage),
        'next_feeding':   next_feeding_time,
        'errors':         system_errors[-10:]
    })


@app.route('/api/recent_events', methods=['GET'])
def api_recent_events():
    """Return event-log entries newer than the client's last seen seq.
    The client passes ?since=<seq>; on first load it should pass 0 to
    get everything still in the buffer.
    """
    try:
        since = int(request.args.get('since', '0'))
    except (TypeError, ValueError):
        since = 0
    return jsonify({'events': get_events_since(since)})


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def main():
    print("=" * 60)
    print(f"Fish Feeding System - Hotel {HOTEL_NUMBER}")
    print(f"Version: v7.7")
    print("=" * 60)

    # Load webhook from sidecar file (no-op if file is missing).
    try:
        load_webhook()
    except Exception as e:
        print(f"[MAIN] load_webhook failed (continuing): {e}")

    # Announce on Slack that we're back up and which software version is
    # running — useful so an operator watching the channel knows the Pi
    # rebooted (or restarted from a crash) and what's now in charge.
    # Wrapped so a network failure here doesn't block the rest of startup.
    try:
        send_slack_notification(f"Fish feeder Hotel {HOTEL_NUMBER} online — software v7.7")
    except Exception as e:
        print(f"[MAIN] Startup Slack notification failed (continuing): {e}")

    # Each startup step is wrapped so a single failure (broken serial port,
    # camera stuck, MQTT broker down) doesn't prevent the web UI from coming
    # up — the operator needs the UI in order to diagnose and recover.
    print("[MAIN] Initializing system...")
    try:
        SetupSystemBoot()
    except Exception as e:
        print(f"[MAIN] SetupSystemBoot failed (continuing): {e}")
        traceback.print_exc()
        system_errors_append(f"Startup SetupSystemBoot error: {e}")

    try:
        load_config()
    except Exception as e:
        print(f"[MAIN] load_config failed (continuing): {e}")
        system_errors_append(f"Startup load_config error: {e}")

    try:
        setup_mqtt()
    except Exception as e:
        print(f"[MAIN] setup_mqtt failed (continuing): {e}")
        system_errors_append(f"Startup setup_mqtt error: {e}")

    try:
        ReadTempHum()
    except Exception as e:
        print(f"[MAIN] ReadTempHum failed (continuing): {e}")
        system_errors_append(f"Startup ReadTempHum error: {e}")

    # Pre-initialise camera so the first page load is fast.
    # Done synchronously here (not in a thread) to avoid a race condition
    # where a Flask worker thread could also try to initialise the camera
    # in parallel — libcamera holds an exclusive lock and the second attempt
    # would fail with "Camera in Acquired state".
    try:
        get_camera()
    except Exception as e:
        print(f"[MAIN] get_camera failed (continuing): {e}")
        system_errors_append(f"Startup get_camera error: {e}")

    # Start food-level analysis loop (migrated from v3.4) — runs immediately
    # then every FOOD_ANALYSIS_INTERVAL seconds in the background.
    threading.Thread(target=_food_analysis_loop, daemon=True, name="FoodAnalysis").start()

    # Start hourly temperature/humidity logger — appends to TEMP_HUM_LOG_FILE
    # so the /temp_hum_log page always has up to 24 hours of history.
    threading.Thread(target=_temp_hum_log_loop, daemon=True, name="TempHumLog").start()

    # Start scheduled-feed timing loop — fires RunFoodSequence whenever one
    # of the up-to-10 fixed feed times set on the "Feeding times per 24 hour"
    # page is reached (v7.2; previously driven by Feeds per 24 hours).
    threading.Thread(target=CheckFeedTiming, daemon=True, name="FeedTiming").start()

    # Start tube-dry idle loop — walks the rotor between feeds when the
    # "Tube dry" checkbox is on, parking at each port for tube_dry_time minutes.
    threading.Thread(target=IdleTubeDry, args=(tube_dry_time,), daemon=True, name="IdleTubeDry").start()

    print(f"[MAIN] Starting web server on port {WEB_PORT}...")
    print(f"[MAIN] Access at http://<raspberry_pi_ip>:{WEB_PORT}")

    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, threaded=True)


if __name__ == '__main__':
    main()


# ==============================================================================
# DEPENDENCIES
# ==============================================================================
#
# System packages (Raspberry Pi OS Bookworm):
#   - python3, libcamera (pre-installed on Bookworm)
#   - rpi-lgpio  (drop-in replacement for python3-rpi.gpio; needed because
#                 RPi.GPIO's edge detection is broken on kernel 6.6+)
#
# Python packages:
#   pip install pyserial adafruit-circuitpython-ahtx0 paho-mqtt requests \
#               flask picamera2 pillow numpy opencv-python-headless
#
# Sidecar files (created automatically under /home/pi/Documents/ if absent):
#   webhook.txt          - optional Slack webhook URL (overrides hardcoded)
#   last_feed.txt        - persisted scheduled-feed anchor timestamp
#   temp_hum_log.csv     - rolling 5-day hourly temperature/humidity log
#
# ==============================================================================
