"""
Standalone Worker Daemon Launcher
Run without Discord: python scripts/run_workers.py
"""

import asyncio
import signal
import sys
from pathlib import Path

# Ensure project root is on the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.worker_daemon import AgentWorkerDaemon


async def main():
    daemon = AgentWorkerDaemon()

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_running_loop()

    def _shutdown():
        print("\n🛑 Shutdown signal received — stopping workers...")
        asyncio.create_task(daemon.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    print(
        f"🚀 Starting worker daemon for: {', '.join(daemon.agent_types)}\n"
        "Press Ctrl+C to stop.\n"
    )

    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
