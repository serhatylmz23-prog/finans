# setup.py
from setuptools import setup, find_packages

setup(
    name="SyFinansOtagi",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.29.0",
        "python-multipart>=0.0.9",
        "python-dotenv>=1.0.0",
        "requests>=2.26.0",
        "yfinance>=0.2.40",
        "opencv-python>=4.5.0",
        "pytesseract>=0.3.0",
        "easyocr>=1.6.0",
        "Pillow>=9.0.0",
        "numpy>=1.21.0",
    ],
    entry_points={
        "console_scripts": [
            "syfinans=main:calistir",
        ]
    }
)