from setuptools import setup, find_packages
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


setup(
    name='MT5pytrader',
    version='0.61',
    description = "MT5pytrader",
    long_description = long_description,
    long_description_content_type="text/markdown",
    license='MIT',
    author="Raimi Azeez Babatunde",
    author_email='raimiazeez26@gmail.com',
    packages=['MT5pytrader'],
    url='https://github.com/raimiazeez26/MT5pytrader',
    keywords=['MT5pytrader', 'python', 'Metatrader5', 'MT5', 'algotrading',
             'autroading'],
    install_requires=[
          'MetaTrader5',
      ],
    zip_safe = False

)