"""
avwx_api_core Package Setup
"""

from setuptools import setup, find_packages


setup(
    name="avwx-api-core",
    version="0.1.0",
    description="Core components for AVWX APIs",
    url="https://github.com/avwx-rest/avwx-api-core",
    author="Michael duPont",
    author_email="michael@mdupont.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires=">= 3.7",
    install_requires=[
        "dicttoxml~=1.7",
        "dnspython~=2.1",
        "motor~=2.3",
        "pyyaml~=5.4",
        "quart>=0.14",
        "quart-openapi>=1.7.1",
        "voluptuous~=0.12",
    ],
    packages=find_packages(),
    tests_require=["pytest-asyncio~=0.14"],
)
