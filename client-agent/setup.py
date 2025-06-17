#!/usr/bin/env python3
"""
Setup script for M5Stack NAS Monitor Client Agent
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="m5stack-nas-monitor",
    version="1.0.0",
    author="M5Stack NAS Monitor Team",
    author_email="admin@example.com",
    description="Client agent for M5Stack NAS monitoring system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/m5stack-nas-monitor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Hardware",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyserial>=3.5",
        "psutil>=5.8.0",
        "netifaces>=0.11.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ],
    },
    entry_points={
        "console_scripts": [
            "m5nas-monitor=m5nas_monitor.daemon:main",
            "m5nas-test=m5nas_monitor.test:main",
        ],
    },
    include_package_data=True,
    package_data={
        "m5nas_monitor": ["config/*.conf", "systemd/*.service"],
    },
)