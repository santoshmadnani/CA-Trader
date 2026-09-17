import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Sensitive patterns to mask in logs
MASK_PATTERNS = [
    (re.compile(r'(access_token["\']?\s*[:=]\s*["\']?)([^"\'\s,}{]+)', re.IGNORECASE), r'\1***MASKED***'),
    (re.compile(r'(authorization["\']?\s*[:=]\s*["\']?Bearer\s+)([^"\'\s,}{]+)', re.IGNORECASE), r'\1***MASKED***'),
    (re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s,}{]+)', re.IGNORECASE), r'\1***MASKED***'),
    (re.compile(r'(api_key["\']?\s*[:=]\s*["\']?)([^"\'\s,}{]+)', re.IGNORECASE), r'\1***MASKED***'),
    (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)([^"\'\s,}{]+)', re.IGNORECASE), r'\1***MASKED***'),
]

class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, repl in MASK_PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True

def setup_logger(name: str = "ca-trader") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(log_format)
    ch.addFilter(SensitiveDataFilter())
    logger.addHandler(ch)

    # Rotating File Handler
    log_dir = Path(os.getenv("CA_TRADER_DATA_DIR", "/app/data")) / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / "ca_trader.log"
    except Exception:
        file_path = Path("ca-trader.log")

    try:
        fh = RotatingFileHandler(
            file_path,
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=5,
            encoding='utf-8'
        )
        fh.setLevel(logging.INFO)
        fh.setFormatter(log_format)
        fh.addFilter(SensitiveDataFilter())
        logger.addHandler(fh)
    except Exception as e:
        logger.warning(f"Could not initialize rotating file logger at {file_path}: {e}")

    return logger

logger = setup_logger()

