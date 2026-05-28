import argparse
import asyncio
import hashlib
import logging
import math
import os

from bleak import BleakClient, BleakScanner
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")

SERVICE_UUID = "4FAFC201-1FB5-459E-8FCC-C5C9C331914B"
CHARACTERISTIC_TX_UUID = "62ec0272-3ec5-11eb-b378-0242ac130003"
CHARACTERISTIC_OTA_UUID = "62ec0272-3ec5-11eb-b378-0242ac130005"

COMMAND_TIMEOUT = 15
ERASE_TIMEOUT = 120
ACK_TIMEOUT = 15
FINAL_TIMEOUT = 60
PACKET_SIZE = 510


async def _discover_meshtastic_device(name: str):
    log.info(f"Searching for '{name}'...")
    esp32 = None

    devices = await BleakScanner.discover()
    for device in devices:
        if device.name == name:
            esp32 = device

    if esp32 is not None:
        log.info(f"'{name}' found!")
    else:
        log.error(f"'{name}' has not been found.")
        exit(-2)

    return esp32


async def send_ota(name, file_path):
    queue = asyncio.Queue()
    done = False
    firmware_size, firmware_sha256 = _get_firmware_metadata(file_path)

    esp32 = await _discover_meshtastic_device(name)

    def disconnect_callback(client):
        if not done:
            log.warning("OTA device disconnected without warning")
            exit(-1)

    async with BleakClient(esp32, disconnected_callback=disconnect_callback) as client:
        def _ota_notification_handler(sender, data: bytearray):
            queue.put_nowait(bytes(data))

        await client.start_notify(CHARACTERISTIC_TX_UUID, _ota_notification_handler)

        total_packets = math.ceil(firmware_size / PACKET_SIZE)
        log.info(f"Firmware size: {firmware_size} bytes")
        log.info(f"Firmware SHA-256: {firmware_sha256}")
        log.info(f"Sending packet size: {PACKET_SIZE}.")
        log.info(f"Total packets to be sent: {total_packets}")

        await _write_command(client, "VERSION")
        version_response = await _expect_response(queue, "OK", COMMAND_TIMEOUT)
        log.info(f"Device version response: {version_response}")

        await _write_command(client, f"OTA {firmware_size} {firmware_sha256}")
        while True:
            response = await _read_response(queue, ERASE_TIMEOUT)
            if response == "ERASING":
                log.info("Device is erasing flash...")
                continue
            if response == "OK":
                log.info("Device is ready to receive firmware")
                break
            _raise_unexpected_response(response, "ERASING or OK")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            MofNCompleteColumn(),
        ) as progress:
            task = progress.add_task("Uploading...", total=total_packets)
            with open(file_path, "rb") as file:
                while chunk := file.read(PACKET_SIZE):
                    await client.write_gatt_char(
                        CHARACTERISTIC_OTA_UUID, chunk, response=False
                    )
                    await _expect_response(queue, "ACK", ACK_TIMEOUT)
                    progress.advance(task)

        final_response = await _read_response(queue, FINAL_TIMEOUT)
        if final_response != "OK":
            _raise_unexpected_response(final_response, "OK")

        log.info("OTA upload completed successfully. Device should reboot shortly.")
        done = True


def _get_firmware_metadata(file_path):
    firmware_size = os.path.getsize(file_path)
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(1024 * 1024):
            sha256.update(chunk)

    return firmware_size, sha256.hexdigest()


async def _write_command(client, command):
    log.debug(f"Sending command: {command}")
    await client.write_gatt_char(
        CHARACTERISTIC_OTA_UUID, f"{command}\n".encode("ascii"), response=False
    )


async def _read_response(queue, timeout):
    try:
        data = await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Timed out waiting for device response after {timeout}s") from exc

    response = data.decode("utf-8", errors="replace").strip("\x00\r\n ")
    if response.startswith("ERR"):
        raise RuntimeError(f"Device returned error: {response}")
    if not response:
        raise RuntimeError(f"Device returned an empty response: {data!r}")
    log.debug(f"Received response: {response}")
    return response


async def _expect_response(queue, expected, timeout):
    response = await _read_response(queue, timeout)
    if response == expected or response.startswith(f"{expected} "):
        return response
    _raise_unexpected_response(response, expected)


def _raise_unexpected_response(response, expected):
    raise RuntimeError(f"Expected {expected}, received: {response}")


def main():
    parser = argparse.ArgumentParser(
        prog="ble_ota.py",
        description="Performs an OTA update via BLE of a meshtastic firmware",
    )
    parser.add_argument(
        "-f", "--filename", required=True, help="update.bin firmware to be flashed"
    )
    parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="Name of the device to connect to. For Example 'Meshtastic_857c'",
    )
    args = parser.parse_args()

    asyncio.run(send_ota(args.name, args.filename))


if __name__ == "__main__":
    main()
