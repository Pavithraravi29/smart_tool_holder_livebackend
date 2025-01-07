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


# Add this at the top of your file with other global variables
global_id = 1  # To maintain ID across reconnections


async def monitor_data(com_port, websocket):
    ser = None
    global global_id  # Add this line to access the global ID

    while True:  # Outer loop for reconnection
        try:
            if ser is None or not ser.is_open:
                try:
                    if ser is not None:
                        ser.close()
                    await asyncio.sleep(1)
                    ser = serial.Serial(com_port, 1000000)
                except serial.SerialException as e:
                    print(f"Failed to open serial port: {e}")
                    await asyncio.sleep(5)
                    continue

            averaging_window = 10
            raw_voltage_queue = np.zeros((4, averaging_window))
            filtered_voltage = np.zeros(4)
            index = 0
            alpha = 0.1
            global randata

            vref = 2.182
            pga = 4
            voltage_offset = np.array([-100.45, 21.50, 0, 0])

            while True:
                try:
                    if not ser.is_open:
                        raise serial.SerialException("Port closed unexpectedly")

                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        parts = line.split(' ')
                        if len(parts) == 5:
                            try:
                                raw_values = np.array([float(i) for i in parts[:4]])
                                rssi = int(parts[4])

                                raw_voltage_values = ((2 * vref) / (pga * 8388607)) * raw_values * 1000
                                raw_voltage_values -= voltage_offset

                                filtered_voltage = (
                                        alpha * raw_voltage_values + (1 - alpha) * filtered_voltage
                                )

                                raw_voltage_queue[:, index % averaging_window] = filtered_voltage
                                index += 1

                                avg_voltage_values = np.mean(raw_voltage_queue, axis=1)

                                current_time = datetime.datetime.now()
                                elapsed_time = (current_time - initial_time).total_seconds()

                                async with id_lock:
                                    data_dict = {
                                        "id": global_id,  # Use global_id instead of did
                                        "tension": float(filtered_voltage[0]),
                                        "torsion": float(filtered_voltage[1]),
                                        "bending_moment_x": float(raw_voltage_values[0]),
                                        "bending_moment_y": float(raw_voltage_values[1]),
                                        "time_seconds": round(elapsed_time, 2),
                                        "temperature": rssi,
                                    }

                                    randata = data_dict
                                    serialized_data = json.dumps(data_dict)

                                    await websocket.send(serialized_data)
                                    print(data_dict)
                                    global_id += 1  # Increment global_id instead of did
                                    await asyncio.sleep(0.1)

                            except ValueError:
                                continue

                except serial.SerialException as e:
                    print(f"Serial connection error: {e}")
                    if ser and ser.is_open:
                        ser.close()
                    ser = None
                    await asyncio.sleep(5)
                    break

        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed, returning to main loop for reconnection...")
            if ser and ser.is_open:
                ser.close()
            ser = None
            return
        except Exception as e:
            print(f"Unexpected error: {e}")
            if ser and ser.is_open:
                ser.close()
            ser = None
            await asyncio.sleep(5)
            return
        finally:
            if ser and ser.is_open:
                ser.close()

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
    max_retries = 5
    retry_delay = 5

    while True:  # Main loop for continuous operation
        try:
            # Start the servers
            server_register = await serve(send_register_data, "172.18.101.47", 5677)
            server_data = await serve(send_random_data, "172.18.101.47", 5676)
            server_additional_data = await serve(send_additional_data, "172.18.101.47", 5678)

            retries = 0
            while retries < max_retries:  # Connection retry loop
                try:
                    async with websockets.connect("ws://172.18.101.47:5676",
                                                  ping_interval=20,  # Reduced ping interval
                                                  ping_timeout=20,  # Reduced ping timeout
                                                  close_timeout=10  # Added close timeout
                                                  ) as websocket:
                        print("WebSocket connection established")
                        retries = 0  # Reset retry counter on successful connection

                        monitor_task = asyncio.create_task(monitor_data(com_port, websocket))
                        await monitor_task  # Wait for the monitor task to complete or raise an exception

                except websockets.exceptions.ConnectionClosed:
                    retries += 1
                    print(f"Connection attempt {retries}/{max_retries} failed, retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    continue

            print("Max retries reached, restarting servers...")
            # Close servers before restarting
            server_register.close()
            server_data.close()
            server_additional_data.close()
            await server_register.wait_closed()
            await server_data.wait_closed()
            await server_additional_data.wait_closed()
            await asyncio.sleep(retry_delay)

        except Exception as e:
            print(f"Server error: {e}")
            await asyncio.sleep(retry_delay)


if __name__ == "__main__":
    asyncio.run(main('COM3'))