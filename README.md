# ble_ota.py

A simple BLE OTA uploader for meshtastic devices, can be used to test BLE OTA.

## Installation and Usage

1. Create a **virtualenv**

   ```bash
   python3 -m venv .venv
   pip install -r requirements.txt
   . ./.venv/bin/activate
   ```

2. Reboot the device into the BLE OTA firmware

   ```bash
   $ ./meshtastic --reboot-ota
   Connected to radio
   INFO file:node.py rebootOTA line:562 Telling node to reboot to OTA in 10 seconds
   ```

3. Upload the update firmware to the device
   ```bash
   $ python3 ble_ota.py -f ~/Downloads/firmware-2.2.23/firmware-tbeam-2.2.23.5672e68-update.bin -n "Meshtastic_6554"
   [19:10:29] INFO     Searching for 'Meshtastic_6554'...                                              ble_ota.py:31
   [19:10:34] INFO     'Meshtastic_6554' found!                                                        ble_ota.py:40
   [19:10:35] INFO     Sending packet size: 510.                                                       ble_ota.py:84
              INFO     Total packets to be sent: 4106                                                  ble_ota.py:85
   Uploading... ━━╸━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   7% 0:03:45  299/4106
   ```

## Notes

There is no real error handling if the upload fails part way through as the BLE OTA protocol
doesn't provide any real recovery mechinisms other than retrying. Manually updating via a serial cable
is always an option.
