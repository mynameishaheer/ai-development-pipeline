"""
Launch the AI Dev Pipeline web dashboard on port 8080.

Usage:
    venv/bin/python scripts/run_dashboard.py

Access at:
    http://<vm-ip>:8080

To expose publicly via Cloudflare Tunnel at dashboard.devbot.site,
add the following ingress rule to ~/.cloudflared/config.yml BEFORE running:

    - hostname: dashboard.devbot.site
      service: http://localhost:8080
"""

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.dashboard:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info",
    )
