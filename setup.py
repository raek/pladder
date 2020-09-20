import setuptools

setuptools.setup(
    name="pladder",
    version="0.0.1",
    author="Rasmus Bondesson",
    author_email="raek@raek.se",
    description="An IRC bot",
    url="https://github.com/raek/pladder",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "pladder-bot = pladder.bot:main",
            "pladder-cli = pladder.cli:main",
            "pladder-irc = pladder.irc.main:main",
        ],
    },
)
