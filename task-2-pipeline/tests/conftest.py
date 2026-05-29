"""
conftest.py — pytest configuration for the task-2-pipeline test suite.

Adds the src/ directory to sys.path so tests can import pipeline modules
directly (e.g. `from transform import transform_weather_data`) without
needing package-relative imports or install steps.

Run all tests from the task-2-pipeline/ directory:
    pytest tests/
"""

# Standard library
import os
import sys

# Add src/ to path so test files can import pipeline modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
