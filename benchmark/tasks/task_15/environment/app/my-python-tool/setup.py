from setuptools import setup, find_packages

setup(
    name="my-python-tool",
    version="1.0.0",
    description="A Python tool for data processing and validation",
    author="Developer",
    packages=find_packages(),
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'my-python-tool=main:main',
        ],
    },
)
