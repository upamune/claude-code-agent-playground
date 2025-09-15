#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "claude-code-sdk==0.0.22",
# ]
# requires-python = ">=3.11"
# ///

import asyncio
from claude_code_sdk import ClaudeSDKClient


async def main():
    async with ClaudeSDKClient() as client:
        await client.query("Hello Claude")
        async for message in client.receive_response():
            print(message)


asyncio.run(main())
