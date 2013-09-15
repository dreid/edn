from setuptools import setup


setup(
    name='edn',
    version='0.0.1',
    py_modules=['edn'],
    install_requires=[
        'parsley>=1.1pre1',
        'pytz',
    ],
)
