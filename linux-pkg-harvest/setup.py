from setuptools import setup, find_packages



with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="linux-pkg-harvest",
    version="0.1.0",
    author="",
    author_email="",
    description="A tool for harvesting package information from Linux distribution repositories",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3"
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "repoharvest=pkgharvest.cli:main",
        ],
    },
)

#