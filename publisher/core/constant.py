"""This module defines various constants used throughout the application"""

from enum import Enum


class RetryConstants(Enum):
    """Constants for controlling retry behavior"""

    MAX_RETRIES = 1
    RETRY_DELAY = 1  # seconds
