# run_tests.py
import pytest
import sys
import os
import datetime
import logging

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/spi_validation.log"
    report_file = f"logs/spi_report_{timestamp}.html"

    # Set up Python Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("🚀 Starting SPI Validation Framework...")
    
    args = [
        "-v",
        "-s",
        f"--html={report_file}",
        "--self-contained-html",
        "tests/"
    ]
    
    exit_code = pytest.main(args)
    logging.info(f"Test suite finished with exit code: {exit_code}")
    sys.exit(exit_code)