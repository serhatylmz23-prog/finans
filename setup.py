# setup.py
from setuptools import setup, find_packages

setup(
    name="SyFinansOtagi",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "flask",
        "flask-cors",
        "requests",
        "opencv-python",
        "pytesseract",
        "easyocr",
        "numpy",
        "scikit-learn",
        "plyer",
        "deep-translator"
    ],
    entry_points={
        "console_scripts": [
            "syfinans=main:main",
        ]
    }
)