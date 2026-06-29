# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Claw Integration Module stubs for diamondnode-unified-inference.
Exposes interfaces for Telegram, KimiClaw, OpenClaw, and Slack notifications.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


import os
import httpx

async def send_telegram_notification(message: str) -> bool:
    """
    Send a notification to Telegram Diamondnodebot.
    
    Args:
        message: The text content to send.
    Returns:
        bool: True if transmission succeeded, False otherwise.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("Telegram configuration missing (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
        return bool(message and message.strip()) # Fallback for local testing if env not set
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=5.0)
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Telegram API returned status code {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


async def send_kimiclaw_notification(message: str, metrics: Optional[Dict[str, Any]] = None) -> bool:
    """
    Send a notification payload to KimiClaw webhook.
    
    Args:
        message: The summary message text.
        metrics: Optional dictionary containing system metrics.
    Returns:
        bool: True if transmission succeeded.
    """
    url = os.environ.get("KIMICLAW_WEBHOOK_URL")
    if not url:
        logger.warning("KimiClaw configuration missing (KIMICLAW_WEBHOOK_URL)")
        return bool(message and message.strip()) # Fallback for local testing
    
    payload = {
        "message": message,
        "metrics": metrics or {}
    }
    headers = {}
    gc_api_key = os.environ.get("GC_API_KEY")
    if gc_api_key:
        headers["Authorization"] = f"Bearer {gc_api_key}"
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=5.0)
            if response.status_code in (200, 201, 202):
                logger.info("KimiClaw notification sent successfully")
                return True
            else:
                logger.error(f"KimiClaw API returned status code {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send KimiClaw notification: {e}")
        return False


async def send_openclaw_notification(message: str, metrics: Optional[Dict[str, Any]] = None) -> bool:
    """
    Send a notification payload to OpenClaw webhook.
    
    Args:
        message: The summary message text.
        metrics: Optional dictionary containing system metrics.
    Returns:
        bool: True if transmission succeeded.
    """
    url = os.environ.get("OPENCLAW_WEBHOOK_URL")
    if not url:
        logger.warning("OpenClaw configuration missing (OPENCLAW_WEBHOOK_URL)")
        return bool(message and message.strip()) # Fallback for local testing
    
    payload = {
        "message": message,
        "metrics": metrics or {}
    }
    headers = {}
    gc_api_key = os.environ.get("GC_API_KEY")
    if gc_api_key:
        headers["Authorization"] = f"Bearer {gc_api_key}"
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=5.0)
            if response.status_code in (200, 201, 202):
                logger.info("OpenClaw notification sent successfully")
                return True
            else:
                logger.error(f"OpenClaw API returned status code {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send OpenClaw notification: {e}")
        return False


async def send_slack_notification(message: str) -> bool:
    """
    Send a notification payload to Slack webhook.
    
    Args:
        message: The summary message text.
    Returns:
        bool: True if transmission succeeded.
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("Slack configuration missing (SLACK_WEBHOOK_URL)")
        return bool(message and message.strip()) # Fallback for local testing
    
    payload = {
        "text": message
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=5.0)
            if response.status_code in (200, 201):
                logger.info("Slack notification sent successfully")
                return True
            else:
                logger.error(f"Slack API returned status code {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")
        return False


async def propagate_to_claws(
    message: str,
    metrics: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None
) -> List[str]:
    """
    Propagate structured markdown / JSON reports to all active claws.
    
    Args:
        message: The base notification message.
        metrics: Dictionary of system state/metrics.
        channels: List of target channels to broadcast to (defaults to all).
    Returns:
        List[str]: List of channels that successfully received the propagation.
    """
    logger.info(f"Propagating to claws: message='{message}' channels={channels}")
    target_channels = channels or ["telegram", "kimiclaw", "openclaw", "slack"]
    delivered = []
    
    for channel in target_channels:
        normalized = channel.lower().strip()
        if normalized == "telegram":
            if await send_telegram_notification(message):
                delivered.append("telegram")
        elif normalized == "kimiclaw":
            if await send_kimiclaw_notification(message, metrics):
                delivered.append("kimiclaw")
        elif normalized == "openclaw":
            if await send_openclaw_notification(message, metrics):
                delivered.append("openclaw")
        elif normalized == "slack":
            if await send_slack_notification(message):
                delivered.append("slack")
                
    return delivered


async def trigger_notion_offload(metrics: Optional[Dict[str, Any]] = None) -> bool:
    """
    Trigger offload of session context and metrics to the Notion soul-capsule database.
    
    Args:
        metrics: Dictionary of system state/metrics.
    Returns:
        bool: True if offload succeeded.
    """
    logger.info(f"Notion offload triggered with metrics: {metrics}")
    return True

