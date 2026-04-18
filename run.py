#!/usr/bin/env python3
"""
Superhero Mail — FastAPI entry point.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5001, reload=False)
