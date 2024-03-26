# CycloneDDS Insight

A graphical tool to visualize the current DDS system.

## How to run via python

```bash
cd cyclonedds/tools/insight

# Install dependencies
python3 -m pip install -r requirements.txt

# Execute
pyside6-rcc ./resources.qrc -o ./src/qrc_file.py && python3 ./src/main.py
```

## How to build a standalone MacOS App

```bash
cd cyclonedds/tools/insight

# Execute
pyside6-rcc ./resources.qrc -o ./src/qrc_file.py &&\
DYLD_LIBRARY_PATH="$CYCLONEDDS_HOME/lib" \
pyinstaller main.spec --noconfirm --clean
```

The app is located at `./dist/CycloneDDS Insight.app` after the build.
