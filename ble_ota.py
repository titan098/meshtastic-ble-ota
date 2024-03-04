import argparse
import asyncio
import logging

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

TX_SEND_MORE = bytearray.fromhex("00")


async def _search_for_esp32(name: str):
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
    firmware = []
    done = False

    esp32 = await _search_for_esp32(name)

    def disconnect_callback(client):
        if not done:
            log.error("OTA device disconnected without warning")
            exit(-1)

    async with BleakClient(esp32, disconnected_callback=disconnect_callback) as client:

        async def _ota_notification_handler(sender: int, data: bytearray):
            if data == TX_SEND_MORE:
                await queue.put("more")
            else:
                log.warn(
                    f"Unknown response on TX channel: sender: {sender}, data: {data}"
                )

        # subscribe to OTA control
        await client.start_notify(CHARACTERISTIC_TX_UUID, _ota_notification_handler)

        # compute the packet size
        # packet_size = (client.mtu_size - 3)
        packet_size = 510

        # split the firmware into packets
        with open(file_path, "rb") as file:
            while chunk := file.read(packet_size):
                firmware.append(chunk)

        # write the packet size to OTA Data
        log.info(f"Sending packet size: {packet_size}.")
        log.info(f"Total packets to be sent: {len(firmware)}")

        # wait for the response
        await asyncio.sleep(1)

        # sequentially write all packets to OTA data
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            MofNCompleteColumn(),
        ) as progress:
            task = progress.add_task("Uploading...", total=len(firmware))
            for _, pkg in enumerate(firmware):
                await client.write_gatt_char(
                    CHARACTERISTIC_OTA_UUID, pkg, response=False
                )
                progress.advance(task)
                if await queue.get() == "more":
                    log.debug("More data requested")
        done = True


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
