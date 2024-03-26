import asyncio
import json
import datetime
import random
from websockets import connect, serve
from bleak import BleakClient

did = 1
initial_time = datetime.datetime.now()
randata = {}
id_lock = asyncio.Lock()

async def register_data():
    register_dict = {
        "register": 1,
        "id": random.randint(1, 10),
        "serial_number": random.randint(1, 990),
        "channel": random.randint(1, 100),
        "device_type": random.choice(["type1", "type2", "type3"]),
        "battery_percentage": random.randint(0, 100)
    }
    return register_dict

async def notification_handler(sender: int, data: bytearray, websocket):
    global did
    global initial_time
    global randata

    try:
        decoded_data = data.decode('utf-8')
        data_val = decoded_data.split(' ')
        print(data_val)
        if len(data_val) >= 6:  # Check if there are at least three elements in the list
            current_time = datetime.datetime.now()
            elapsed_time = (current_time - initial_time).total_seconds()

            async with id_lock:
                insert_tuple = (
                    did,
                    (float(data_val[0]) + 2) * 8,
                    (float(data_val[1]) + 2) * 8,
                    (float(data_val[2]) + 2) * 8,
                    (float(data_val[1]) + 3) * 7,
                    elapsed_time,
                    random.uniform(25.6, 29.7)
                )

                data_dict = {
                    "id": did,
                    "tension": float(data_val[1]),
                    "torsion": float(data_val[2]),
                    "bending_moment_x": float(data_val[3]),
                    "bending_moment_y": float(data_val[3]),  # Adjust as needed
                    "time_seconds": round(elapsed_time, 2),
                    "temperature": random.uniform(25.6, 29.7),
                    # "battery_percentage": random.randint(0, 100)
                }

                randata = data_dict
                serialized_data = json.dumps(data_dict)

                await websocket.send(serialized_data)
                print(data_dict)
                did += 1
                await asyncio.sleep(0.1)
        else:
            print("Received incomplete data.")

    except Exception as e:
        print(f"Error processing notification: {e}")

async def monitor_data(address, websocket):
    async with BleakClient(address) as client:
        characteristic_uuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
        await client.start_notify(characteristic_uuid, lambda sender, data: asyncio.ensure_future(
            notification_handler(sender, data, websocket)))

        try:
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(f"Error monitoring data: {e}")

async def send_register_data(websocket, path):
    registration_data = await register_data()
    await websocket.send(json.dumps(registration_data))

async def send_random_data(websocket, path):
    while True:
        await websocket.send(json.dumps(randata))
        await asyncio.sleep(0.1)

async def send_additional_data(websocket, path):
    while True:
        additional_data = {
            "battery_percentage": random.randint(0, 100),
            "RSSI": random.randint(0, 4),
            "temperature": round(random.uniform(20.0, 25.0), 2),
            "packet_error": random.randint(0, 100),
        }
        await websocket.send(json.dumps(additional_data))
        await asyncio.sleep(5)


async def main(address):
    server_register = await serve(send_register_data, "172.18.101.47", 5677)
    server_data = await serve(send_random_data, "172.18.101.47", 5676)
    server_additional_data = await serve(send_additional_data, "172.18.101.47", 5678)
    
    async with connect("ws://172.18.101.47:5676") as websocket:
        asyncio.create_task(monitor_data(address, websocket))

        try:
            await server_register.serve_forever()
            await server_data.serve_forever()
            await server_additional_data.serve_forever()
            
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    device_address = "C4:8C:B3:08:58:A3"
    asyncio.run(main(device_address))
