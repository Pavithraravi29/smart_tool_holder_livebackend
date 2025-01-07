# import numpy as np
# import serial
#
# import asyncio
# import json
# import datetime
# import random
# from websockets import connect, serve
#
# did = 1
# initial_time = datetime.datetime.now()
# randata = {}
# id_lock = asyncio.Lock()
#
#
# async def register_data():
#     register_dict = {
#         "register": 1,
#         "id": random.randint(1, 10),
#         "serial_number": random.randint(1, 990),
#         "channel": random.randint(1, 100),
#         "device_type": random.choice(["type1", "type2", "type3"]),
#         "battery_percentage": random.randint(0, 100)
#     }
#     return register_dict
#
#
# async def monitor_data(com_port, websocket):
#         averaging_window = 10
#         raw_voltage_queue = np.zeros((4, averaging_window))
#         filtered_voltage = np.zeros(4)  # To store the filtered voltage
#         index = 0
#         running = True
#         alpha = 0.1  # Smoothing factor for the EMA filter
#         ser = serial.Serial(com_port, 1000000)
#         global randata
#
#         # Constants for voltage calculation
#         vref = 2.182
#         pga = 4
#         voltage_offset = np.array([-100.45, 21.50, 0, 0])
#         did = 1
#
#         try:
#             while True:
#                 try:
#                     line = ser.readline().decode('utf-8').strip()
#                     if line:
#                         parts = line.split(' ')
#                         if len(parts) == 5:  # Expecting 4 voltage values and RSSI
#                             try:
#                                 raw_values = np.array([float(i) for i in parts[:4]])
#                                 rssi = int(parts[4])
#
#                                 # Calculate raw voltage values
#                                 raw_voltage_values = ((2 * vref) / (pga * 8388607)) * raw_values * 1000
#                                 raw_voltage_values -= voltage_offset
#
#                                 # Apply EMA for low-pass filtering
#                                 filtered_voltage = (
#                                         alpha * raw_voltage_values + (1 - alpha) * filtered_voltage
#                                 )
#
#                                 # Update queue with raw voltage values for averaging
#                                 raw_voltage_queue[:, index % averaging_window] = filtered_voltage
#                                 index += 1
#
#                                 # Calculate averaged voltage values
#                                 avg_voltage_values = np.mean(raw_voltage_queue, axis=1)
#
#                                 # print(raw_voltage_values)
#                                 current_time = datetime.datetime.now()
#                                 elapsed_time = (current_time - initial_time).total_seconds()
#
#                                 async with id_lock:
#                                     data_dict = {
#                                         "id": did,
#                                         "tension": float(filtered_voltage[0]),
#                                         "torsion": float(filtered_voltage[1]),
#                                         "bending_moment_x": float(raw_voltage_values[0]),
#                                         "bending_moment_y": float(raw_voltage_values[1]),  # Adjust as needed
#                                         "time_seconds": round(elapsed_time, 2),
#                                         "temperature": rssi,
#                                         # "battery_percentage": random.randint(0, 100)
#                                     }
#
#                                     randata = data_dict
#                                     serialized_data = json.dumps(data_dict)
#
#                                     await websocket.send(serialized_data)
#                                     print(data_dict)
#                                     did += 1
#                                     await asyncio.sleep(0.1)
#
#
#                             except ValueError:
#                                 pass  # Skip lines with invalid data
#                 except serial.SerialException:
#                     break
#
#         except asyncio.CancelledError:
#             pass
#
#         except Exception as e:
#             print(f"Error monitoring data: {e}")
#
#
# async def send_register_data(websocket):
#     registration_data = await register_data()
#     await websocket.send(json.dumps(registration_data))
#
#
# async def send_random_data(websocket):
#     while True:
#         await websocket.send(json.dumps(randata))
#         await asyncio.sleep(0.1)
#
#
# async def send_additional_data(websocket, path):
#     while True:
#         additional_data = {
#             "battery_percentage": random.randint(0, 100),
#             "RSSI": random.randint(0, 4),
#             "temperature": round(random.uniform(20.0, 25.0), 2),
#             "packet_error": random.randint(0, 100),
#         }
#         await websocket.send(json.dumps(additional_data))
#         await asyncio.sleep(5)
#
#
# async def main(com_port):
#     server_register = await serve(send_register_data, "172.18.101.47", 5677)
#     server_data = await serve(send_random_data, "172.18.101.47", 5676)
#     server_additional_data = await serve(send_additional_data, "172.18.101.47", 5678)
#
#     async with connect("ws://172.18.101.47:5676") as websocket:
#         asyncio.create_task(monitor_data(com_port, websocket))
#
#         try:
#             await server_register.serve_forever()
#             await server_data.serve_forever()
#             await server_additional_data.serve_forever()
#
#         except asyncio.CancelledError:
#             pass
#
#
# if __name__ == "__main__":
#     asyncio.run(main('COM3'))
import numpy as np
import serial

import asyncio
import json
import datetime
import random
from websockets import connect, serve
import websockets

did = 1
initial_time = datetime.datetime.now()
randata = {}
id_lock = asyncio.Lock()




async def ping_handler(websocket, path):
    try:
        while True:
            # Handle incoming messages or pings from the server
            await websocket.recv()
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")


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


async def monitor_data(com_port, websocket):
        averaging_window = 10
        raw_voltage_queue = np.zeros((4, averaging_window))
        filtered_voltage = np.zeros(4)  # To store the filtered voltage
        index = 0
        running = True
        alpha = 0.1  # Smoothing factor for the EMA filter
        ser = serial.Serial(com_port, 1000000)
        global randata

        # Constants for voltage calculation
        vref = 2.182
        pga = 4
        voltage_offset = np.array([-100.45, 21.50, 0, 0])
        did = 1

        try:
            while True:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        parts = line.split(' ')
                        if len(parts) == 5:  # Expecting 4 voltage values and RSSI
                            try:
                                raw_values = np.array([float(i) for i in parts[:4]])
                                rssi = int(parts[4])

                                # Calculate raw voltage values
                                raw_voltage_values = ((2 * vref) / (pga * 8388607)) * raw_values * 1000
                                raw_voltage_values -= voltage_offset

                                # Apply EMA for low-pass filtering
                                filtered_voltage = (
                                        alpha * raw_voltage_values + (1 - alpha) * filtered_voltage
                                )

                                # Update queue with raw voltage values for averaging
                                raw_voltage_queue[:, index % averaging_window] = filtered_voltage
                                index += 1

                                # Calculate averaged voltage values
                                avg_voltage_values = np.mean(raw_voltage_queue, axis=1)

                                # print(raw_voltage_values)
                                current_time = datetime.datetime.now()
                                elapsed_time = (current_time - initial_time).total_seconds()

                                async with id_lock:
                                    data_dict = {
                                        "id": did,
                                        "tension": float(filtered_voltage[0]),
                                        "torsion": float(filtered_voltage[1]),
                                        "bending_moment_x": float(raw_voltage_values[0]),
                                        "bending_moment_y": float(raw_voltage_values[1]),  # Adjust as needed
                                        "time_seconds": round(elapsed_time, 2),
                                        "temperature": rssi,
                                        # "battery_percentage": random.randint(0, 100)
                                    }

                                    randata = data_dict
                                    serialized_data = json.dumps(data_dict)

                                    await websocket.send(serialized_data)
                                    print(data_dict)
                                    did += 1
                                    await asyncio.sleep(0.1)


                            except ValueError:
                                pass  # Skip lines with invalid data
                except serial.SerialException:
                    break

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(f"Error monitoring data: {e}")


async def send_register_data(websocket):
    registration_data = await register_data()
    await websocket.send(json.dumps(registration_data))


async def send_random_data(websocket):
    while True:
        try:
            await websocket.send(json.dumps(randata))
            await asyncio.sleep(0.1)
        except websockets.exceptions.ConnectionClosedError:
            print("Connection closed unexpectedly, reconnecting...")
            await asyncio.sleep(5)  # Wait before retrying
            # Attempt to reconnect or handle as needed
            break  # Or handle a retry mechanism here



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


async def main(com_port):
    server_register = await serve(send_register_data, "172.18.101.47", 5677)
    server_data = await serve(send_random_data, "172.18.101.47", 5676)
    server_additional_data = await serve(send_additional_data, "172.18.101.47", 5678)

    async with websockets.connect("ws://172.18.101.47:5676", ping_interval=60, ping_timeout=120) as websocket:
        asyncio.create_task(monitor_data(com_port, websocket))

        try:
            await server_register.serve_forever()
            await server_data.serve_forever()
            await server_additional_data.serve_forever()



        except websockets.exceptions.ConnectionClosedError:
            print("Connection closed unexpectedly, reconnecting...")
            await asyncio.sleep(5)  # Wait before retrying
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    asyncio.run(main('COM3'))
