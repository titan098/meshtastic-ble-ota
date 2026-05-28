# ble_ota.py

A simple BLE OTA uploader for Meshtastic devices running the unified OTA loader. This uploader supports the newer unified OTA protocol only.

See: https://github.com/meshtastic/esp32-unified-ota

## Installation and Usage

1. Create a **virtualenv**

   ```bash
   python3 -m venv .venv
   . ./.venv/bin/activate
   pip install -r requirements.txt
   ```

2. Reboot the device into the unified BLE OTA firmware

   ```bash
   $ ./meshtastic --reboot-ota
   Connected to radio
   INFO file:node.py rebootOTA line:562 Telling node to reboot to OTA in 10 seconds
   ```

3. Upload the update firmware to the device
    ```bash
      python3 ./ble_ota.py -f ~/Downloads/firmware-esp32-2.7.24.472b14c/firmware-tbeam-2.7.24.472b14c.bin -n "iDEA_6554"
      [13:08:30] INFO     Searching for 'iDEA_6554'...                                                        ble_ota.py:38
      [13:08:35] INFO     'iDEA_6554' found!                                                                  ble_ota.py:47
      [13:08:36] INFO     Firmware size: 2168928 bytes                                                        ble_ota.py:75
                 INFO     Firmware SHA-256: 88423ff88189980e11b9f6491fd1e6ef2bca2802a8f8f5b1ce8bf214c8f7fe3d  ble_ota.py:76
                 INFO     Sending packet size:                                                                ble_ota.py:77
                 INFO     Total packets to be sent: 4253                                                      ble_ota.py:78
                 INFO     Device version response: OK 0 2.7.24.472b14c 2 v1.0.1                               ble_ota.py:82
                 INFO     Device is erasing flash...                                                          ble_ota.py:88
      [13:08:44] INFO     Device is ready to receive firmware                                                 ble_ota.py:91
      Uploading... ━━━━━━━━━━━━━━━━╺━━━━━━━━━━━━━━━━━━━━━━━  41% 0:05:30 1736/4253
    ```

## Protocol

The uploader follows the unified BLE OTA command flow:

1. Send `VERSION\n` and require an `OK ...` response.
2. Send `OTA <size> <sha256>\n` using the update file size and SHA-256 digest.
3. Wait for `ERASING`, then `OK`.
4. Stream firmware chunks and wait for `ACK` after each chunk.
5. Wait for final `OK` after the last chunk.

If the device replies with `ERR ...`, the upload fails immediately. The unified
loader may require the expected firmware hash to be pre-provisioned on the
device before the OTA command is accepted.

## Notes

There is no recovery if the upload fails part way through other than retrying.
Manually updating via a serial cable is always an option.
