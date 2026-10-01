#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform Keep-Awake Manager
Prevents system sleep during XAUUSD trading hours (16:00-23:00 UTC)
Ensures continuous price monitoring and order execution.
"""
import os
import sys
import time
import logging
from datetime import datetime
import pytz
import subprocess

logger = logging.getLogger(__name__)

class PlatformKeepAwake:
    """Manages system keep-awake during trading hours."""

    TRADING_START_UTC = 16  # 16:00 UTC (EUR-US Overlap)
    TRADING_END_UTC = 23    # 23:00 UTC (end of US Evening)

    def __init__(self):
        self.is_windows = sys.platform == "win32"
        self.awake = False
        self.last_heartbeat = 0
        self.heartbeat_interval = 60  # Refresh every 60 seconds

    def is_trading_hours(self) -> bool:
        """Check if current time is within XAUUSD trading window."""
        now = datetime.now(pytz.UTC)
        current_hour = now.hour

        # Trading: 16:00-23:00 UTC daily (5 days/week)
        is_weekday = now.weekday() < 5  # Mon-Fri
        return is_weekday and (self.TRADING_START_UTC <= current_hour < self.TRADING_END_UTC)

    def keep_awake_windows(self) -> bool:
        """
        Prevent Windows system sleep during trading hours.
        Uses native Windows API via PowerShell.
        """
        if not self.is_windows:
            return False

        try:
            # PowerShell command: disable sleep while process runs
            ps_cmd = """
            Add-Type @'
            using System;
            using System.Runtime.InteropServices;
            public class DisplayManager {
                [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
                public static extern void SetThreadExecutionState(uint esFlags);

                public const uint ES_CONTINUOUS = 0x80000000;
                public const uint ES_DISPLAY_REQUIRED = 0x00000002;
                public const uint ES_SYSTEM_REQUIRED = 0x00000001;
            }
            '@ -ErrorAction SilentlyContinue

            [DisplayManager]::SetThreadExecutionState([DisplayManager]::ES_CONTINUOUS -bor [DisplayManager]::ES_SYSTEM_REQUIRED -bor [DisplayManager]::ES_DISPLAY_REQUIRED)
            """

            subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                check=False,
                timeout=5
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set keep-awake on Windows: {e}")
            return False

    def keep_awake_linux(self) -> bool:
        """Prevent Linux system sleep (using systemd-inhibit or similar)."""
        if self.is_windows:
            return False

        try:
            # Use systemd-inhibit to prevent sleep
            subprocess.Popen(
                ["systemd-inhibit", "--what=sleep", "--why=Trading", "--mode=block", "sleep", "999999"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set keep-awake on Linux: {e}")
            return False

    def request_keep_awake(self) -> bool:
        """
        Request platform keep-awake during trading hours.
        Returns True if system is staying awake.
        """
        now = datetime.now(pytz.UTC)

        if self.is_trading_hours():
            # We are in trading hours - ensure system stays awake
            current_time = time.time()

            # Refresh keep-awake heartbeat every 60 seconds
            if current_time - self.last_heartbeat > self.heartbeat_interval:
                if self.is_windows:
                    self.keep_awake_windows()
                else:
                    self.keep_awake_linux()

                self.last_heartbeat = current_time
                self.awake = True

                logger.info(f"[KEEP-AWAKE] Trading hours active ({now.strftime('%H:%M UTC')})")
                return True

            return self.awake
        else:
            # Outside trading hours - allow system sleep
            self.awake = False
            next_trading = self.TRADING_START_UTC
            hours_until = (next_trading - now.hour) % 24

            if hours_until > 0:
                logger.debug(f"[KEEP-AWAKE] Outside trading hours. Next window in {hours_until}h at {next_trading}:00 UTC")

            return False

    def get_trading_status(self) -> dict:
        """Get current trading status and keep-awake state."""
        now = datetime.now(pytz.UTC)
        is_trading = self.is_trading_hours()

        if is_trading:
            next_window = "Next: Tomorrow 16:00 UTC"
        else:
            hours_until = (self.TRADING_START_UTC - now.hour) % 24
            next_window = f"Next: {hours_until}h away at {self.TRADING_START_UTC}:00 UTC"

        return {
            "time_utc": now.strftime("%H:%M:%S"),
            "is_trading": is_trading,
            "keep_awake_active": self.awake,
            "trading_window": f"{self.TRADING_START_UTC}:00-{self.TRADING_END_UTC}:00 UTC",
            "next_window": next_window,
            "platform": "Windows" if self.is_windows else "Linux/Mac"
        }


# Global instance
_keep_awake = PlatformKeepAwake()

def setup_keep_awake():
    """Initialize keep-awake manager (call once at startup)."""
    status = _keep_awake.get_trading_status()
    logger.info(f"Keep-Awake Manager initialized: {status}")
    return _keep_awake

def maintain_keep_awake():
    """Call this regularly (every 30-60 seconds) during trading to prevent sleep."""
    return _keep_awake.request_keep_awake()

def get_keep_awake_status():
    """Get current keep-awake status."""
    return _keep_awake.get_trading_status()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )

    mgr = setup_keep_awake()

    print("\n" + "="*70)
    print("PLATFORM KEEP-AWAKE MANAGER")
    print("="*70)
    print(mgr.get_trading_status())
    print("\nMonitoring for trading hours...")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            mgr.request_keep_awake()
            status = mgr.get_trading_status()

            if status["is_trading"]:
                print(f"[ACTIVE] {status['time_utc']} - Keep-Awake: {status['keep_awake_active']}")
            else:
                print(f"[IDLE] {status['time_utc']} - {status['next_window']}")

            time.sleep(30)
    except KeyboardInterrupt:
        print("\n\nShutdown requested.")
