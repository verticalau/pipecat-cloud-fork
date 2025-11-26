#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""
Pipecat Cloud SDK Helper - Programmatic interface to Pipecat Cloud API.

This module provides an SDK-like interface to manage Pipecat Cloud agents
without subprocess calls or console output. It wraps the internal _API
class to provide a clean, Go-style (nullable error) API suitable for
embedding in Python applications.

Design Principles:
- Go-style error handling: functions return (data, error) tuples where error is nullable
- No console output: all methods return data directly, no printing or logging to console
- Thin wrapper: reuses existing _API implementation without reimplementing logic
- Minimal code: focused on essential functionality, extensible for future features
- Code locality: keeps SDK logic separate from CLI logic

Usage Example:
    from pipecatcloud.pcc_helper import PipecatHelper

    helper = PipecatHelper(token="your-token", org="your-org")
    link, error = await helper.start_agent(
        agent_name="my-agent",
        api_key="public-key",
        use_daily=True
    )
    if error:
        print(f"Error: {error.get('error', 'Unknown error')}")
    else:
        print(f"Started: {link}")

Intended for: Python applications that need programmatic Pipecat Cloud access
Do NOT use: For CLI functionality (use CLI commands directly)
"""

import json

from pipecatcloud.api import _API


class PipecatHelper:
    """SDK helper for programmatic Pipecat Cloud agent management.

    Provides Go-style error handling (nullable errors) and no console output.
    Suitable for embedding in Python applications that need to manage agents
    programmatically.

    Args:
        token: Authentication token for Pipecat Cloud API
        org: Organization ID to operate within
    """

    token: str
    org: str
    _api: _API

    def __init__(self, token: str, org: str):
        """Initialize the helper with authentication credentials.

        Args:
            token: Authentication token (required)
            org: Organization ID (required)
        """
        if not token:
            raise ValueError("token is required")
        if not org:
            raise ValueError("org is required")

        self.token = token
        self.org = org
        self._api = _API(token=token, is_cli=False)

    async def start_agent(
        self,
        agent_name: str,
        api_key: str,
        use_daily: bool = False,
        data: str | None = None,
        daily_properties: str | None = None,
    ) -> str:
        """Start an agent instance and return the session link.

        This method checks agent health before starting, validates inputs,
        and returns a Go-style (link, error) tuple. If use_daily is True
        and the start succeeds, returns a Daily room URL with token.

        Args:
            agent_name: Name of the agent to start (e.g., 'my-agent')
            api_key: Public API key to use for starting the agent
            use_daily: Whether to create a Daily WebRTC session (default: False)
            data: Optional JSON string to pass to the agent
            daily_properties: Optional JSON string with Daily room properties

        Returns:
            Tuple of (link, error) where:
            - link: Session URL string if successful, None otherwise
            - error: Error dict with 'code' and 'error' keys if failed, None otherwise

        Example:
            link, error = await helper.start_agent(
                agent_name="my-agent",
                api_key="pk_...",
                use_daily=True
            )
            if error:
                print(f"Failed: {error['error']}")
            else:
                print(f"Session: {link}")
        """
        if not agent_name:
            raise ValueError("agent_name is required")

        if not api_key:
            raise ValueError("api_key is required")

        if use_daily and daily_properties:
            try:
                json.loads(daily_properties)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format for daily_properties: {str(e)}")

        if data:
            try:
                json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format for data: {str(e)}")

        health_data, health_error = await self._api.agent(agent_name=agent_name, org=self.org)

        if health_error:
            raise ValueError(f"Error checking agent health: {health_error}")

        if not health_data or not health_data.get("ready", False):
            raise ValueError(f"Agent '{agent_name}' does not exist or is not in a healthy state")

        start_data, start_error = await self._api.start_agent(
            agent_name=agent_name,
            api_key=api_key,
            use_daily=use_daily,
            data=data,
            daily_properties=daily_properties,
        )

        if start_error:
            raise ValueError(f"Error starting agent: {start_error}")

        if not start_data:
            raise ValueError("Start request succeeded but returned no data")

        if use_daily and isinstance(start_data, dict):
            daily_room = start_data.get("dailyRoom")
            daily_token = start_data.get("dailyToken")
            if daily_room and daily_token:
                link = f"{daily_room}?t={daily_token}"
                return link

        raise ValueError("Start request succeeded but returned no data")
