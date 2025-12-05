"""
Centralized Logging Configuration
=================================
Provides consistent, configurable logging across all network generators.
Reduces redundancy and enables fine-grained control of verbosity.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class LogLevel:
    """Logging level constants."""
    CRITICAL = logging.CRITICAL  # 50 - Critical errors only
    ERROR = logging.ERROR        # 40 - Errors and above
    WARNING = logging.WARNING    # 30 - Warnings and above
    INFO = logging.INFO          # 20 - General information (default)
    DEBUG = logging.DEBUG        # 10 - Detailed diagnostic information


def setup_logger(
    name: str,
    log_dir: Path = Path('logs'),
    level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True,
    file_prefix: str = 'san',
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup a configured logger with file and/or console output.
    
    Args:
        name: Logger name (usually __name__)
        log_dir: Directory for log files
        level: Logging level (use LogLevel constants)
        console_output: Whether to output to console
        file_output: Whether to output to file
        file_prefix: Prefix for log filename
        format_string: Custom format string (uses default if None)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = setup_logger(__name__, level=LogLevel.INFO)
        >>> logger.info("Processing started")
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()  # Remove any existing handlers
    
    # Default format - simplified for production, detailed for debug
    if format_string is None:
        if level == logging.DEBUG:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        else:
            format_string = '%(asctime)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_output:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f'{file_prefix}_{timestamp}.log'
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Log file location at DEBUG level
        logger.debug(f"Log file: {log_file}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger by name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_log_level(logger: logging.Logger, level: int):
    """
    Change the log level of an existing logger.
    
    Args:
        logger: Logger instance
        level: New logging level
    """
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def disable_external_loggers():
    """
    Reduce verbosity of third-party libraries (matplotlib, urllib3, etc.).
    Call this to reduce noise in logs.
    """
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('networkx').setLevel(logging.WARNING)


# Convenience function for quick setup
def quick_setup(
    module_name: str,
    verbose: bool = False,
    quiet: bool = False
) -> logging.Logger:
    """
    Quick logger setup with common presets.
    
    Args:
        module_name: Name of the module (use __name__)
        verbose: Enable DEBUG level logging
        quiet: Only show WARNING and above
        
    Returns:
        Configured logger
    """
    if quiet:
        level = LogLevel.WARNING
    elif verbose:
        level = LogLevel.DEBUG
    else:
        level = LogLevel.INFO
    
    logger = setup_logger(module_name, level=level)
    
    if not verbose:
        disable_external_loggers()
    
    return logger
