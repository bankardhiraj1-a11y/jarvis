import subprocess
import time
import logging
import os
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [WATCHDOG] %(message)s',
    handlers=[
        logging.FileHandler('watchdog.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ORCHESTRATOR_PROCESS = None
ORCHESTRATOR_CMD = ["python", "agent_orchestrator.py"]
RESTART_DELAY = 5

def is_process_alive(proc):
    """Check if process is still running."""
    if proc is None:
        return False
    return proc.poll() is None

def start_orchestrator():
    """Start the orchestrator process."""
    global ORCHESTRATOR_PROCESS
    try:
        logger.info("Starting Orchestrator...")
        ORCHESTRATOR_PROCESS = subprocess.Popen(
            ORCHESTRATOR_CMD,
            stdout=open('orchestrator.log', 'a'),
            stderr=subprocess.STDOUT,
            cwd=os.getcwd()
        )
        logger.info(f"Orchestrator started (PID: {ORCHESTRATOR_PROCESS.pid})")
        return True
    except Exception as e:
        logger.error(f"Failed to start Orchestrator: {e}")
        return False

def restart_orchestrator():
    """Restart the orchestrator if it crashed."""
    global ORCHESTRATOR_PROCESS
    if ORCHESTRATOR_PROCESS is not None:
        try:
            ORCHESTRATOR_PROCESS.terminate()
            ORCHESTRATOR_PROCESS.wait(timeout=3)
            logger.info("Orchestrator terminated")
        except:
            ORCHESTRATOR_PROCESS.kill()
            logger.info("Orchestrator killed")

    time.sleep(RESTART_DELAY)
    start_orchestrator()

def main():
    """Watchdog main loop."""
    logger.info("[WATCHDOG] Production Supervisor Starting...")

    start_orchestrator()

    while True:
        time.sleep(10)

        if not is_process_alive(ORCHESTRATOR_PROCESS):
            logger.warning("Orchestrator crashed! Restarting...")
            restart_orchestrator()
        else:
            logger.info(f"Orchestrator alive (PID: {ORCHESTRATOR_PROCESS.pid})")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("[WATCHDOG] Shutdown signal received")
        if ORCHESTRATOR_PROCESS:
            ORCHESTRATOR_PROCESS.terminate()
            ORCHESTRATOR_PROCESS.wait()
        logger.info("[WATCHDOG] Cleanup complete")
