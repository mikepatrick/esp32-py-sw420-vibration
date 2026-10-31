ifeq ($(OS), Windows_NT)
    # Let mpremote and esptool detect the connected ESP
    TARGET = auto
    ESPTOOL_PORT =
    VENV_PYTHON = .venv/Scripts/python.exe
else
    # Linux / macOS ESP serial port
    TARGET = /dev/ttyUSB0
    ESPTOOL_PORT = --port $(TARGET)
    VENV_PYTHON = ./.venv/bin/python
endif

.PHONY: all repl push-s3 push-c3 activate erase-flash erase-flash-c3 flash-firmware flash-firmware-c3 setup clean

# Default target when you run just 'make'
all: repl

repl:
	mpremote connect $(TARGET)
push-s3:
	@echo "Pushing files to ESP32-S3 device..."
	mpremote connect $(TARGET) fs cp main-s3.py :main.py + fs cp ssd1306.py :ssd1306.py + fs cp utility.py :utility.py + fs cp .env :.env
push-c3:
	@echo "Pushing files to ESP32-C3 device..."
	mpremote connect $(TARGET) fs cp main-c3.py :main.py + fs cp ssd1306.py :ssd1306.py + fs cp utility.py :utility.py + fs cp .env :.env
activate:
ifeq ($(OS), Windows_NT)
	@echo .\.venv\Scripts\Activate.ps1
else
	@echo source ./.venv/bin/activate
endif
erase-flash:
	esptool --chip esp32s3 $(ESPTOOL_PORT) --baud 115200 erase_flash
erase-flash-c3:
	esptool --chip esp32c3 $(ESPTOOL_PORT) --baud 115200 erase_flash
flash-firmware:
	esptool $(ESPTOOL_PORT) --chip esp32s3 --baud 115200 write-flash 0x0 './ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin'
flash-firmware-c3:
	esptool $(ESPTOOL_PORT) --chip esp32c3 --baud 115200 write-flash 0x0 './ESP32_GENERIC_C3-20260824-v1.29.0.bin'
setup:
	python -m venv .venv
	$(VENV_PYTHON) -m pip install mpremote esptool
	$(VENV_PYTHON) -m pip install --target typings -r requirements-stubs.txt
clean:
ifeq ($(OS), Windows_NT)
	cmd /c rmdir /s /q "C:\Users\mike\workspace\esp32s3-py-sw420-vibration\.venv"
	cmd /c rmdir /s /q "C:\Users\mike\workspace\esp32s3-py-sw420-vibration\typings"
else
	rm -rf ./.venv
	rm -rf typings
endif
