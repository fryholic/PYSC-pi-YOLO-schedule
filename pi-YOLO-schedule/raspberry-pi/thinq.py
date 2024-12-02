import asyncio
from aiohttp import ClientSession
from thinqconnect.thinq_api import ThinQApi
from thinqconnect.mqtt_client import ThinQMQTTClient
import threading

from flask import Flask


import uuid
import awscrt
import json



client_id = str(uuid.uuid4())

device_id = '' 

mqtt_client = None

battery_percent = 0


### 작동 명령에 관한 payload

payload_op_start = {
    "operation": {
        "cleanOperationMode": "START"
    }
}
payload_op_resume = {
    "operation": {
        "cleanOperationMode": "RESUME"
    }
}
payload_op_pause = {
    "operation": {
        "cleanOperationMode": "PAUSE"
    }
}
payload_op_homing = {
    "operation": {
        "cleanOperationMode": "HOMING"
    }
}
payload_op_wake = {
    "operation": {
        "cleanOperationMode": "WAKE_UP"
    }
}

###

payload_timer_start = {
    "timer": {
        "absoluteHourToStart": 20,
        "absoluteMinuteToStart": 15
    }
}

payload_timer_cancel = {
    "timer": {
        "absoluteHourToStart": {"w", 20},
        "absoluteMinuteToStart": {"w", 15}
    }
}

async def test_devices_list():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_device_list()
        device_id = response[0]['deviceId']
        print("device_list : %s", response, device_id)

async def post_devices_control():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_device_list()
        device_id = response[0]['deviceId']
        await thinq_api.async_post_device_control(device_id=device_id, payload=payload_op_start, timeout=30)
        print("response : ", response, device_id)

async def get_devices_status():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_device_list()
        device_id = response[0]['deviceId']
        device_status = await thinq_api.async_get_device_status(device_id=device_id, timeout=30)
        runState = device_status['runState']['currentState']
        battery_percent = device_status['battery']['percent']
        battery_level = device_status['battery']['level']
        print("device status : ", device_status)
        print(runState)
        print(battery_percent)
        print(battery_level)

async def get_event_list():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_event_list()
        print("event : %s", response)

async def devices_control_Start():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_device_list()
        device_id = response[0]['deviceId']
        await thinq_api.async_post_device_control(device_id=device_id, payload=payload_op_start, timeout=30)
        print("response : ", response, device_id)

async def devices_control(payload):
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_device_list()
        device_id = response[0]['deviceId']
        await thinq_api.async_post_device_control(device_id=device_id, payload=payload, timeout=30)
        print("response : ", response, device_id)

async def devices_control_Homing():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_device_list()
        device_id = response[0]['deviceId']
        await thinq_api.async_post_device_control(device_id=device_id, payload=payload_op_homing, timeout=30)
        print("response : ", response, device_id)

async def get_devices_battery_status():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        device_status = await thinq_api.async_get_device_status(device_id=device_id, timeout=30)
        runState = device_status['runState']['currentState']
        battery = device_status['battery']
        battery_level = device_status['battery']['level']
        battery_percent = device_status['battery']['percent']
        print("device status : ", device_status)
        print(runState)
        print(battery)
        print(battery_level)
        print(battery_percent)
        return battery_percent

async def post_devices_event_subscribe():
    global count
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)
        response = await thinq_api.async_get_device_list()
        device_id = response[0]['deviceId']
        result = await thinq_api.async_post_event_subscribe(device_id=device_id)
        print(result)


def on_message_received(topic: str, payload: bytes, dup: bool,
                        qos: awscrt.mqtt.QoS, retain: bool,
                        **kwargs):
    global battery_percent
    print(f"on_message_received: {topic}, {payload}, {dup}, {qos}, {retain}, {kwargs}")
    if isinstance(payload, bytes):
        payload = payload.decode('utf-8')
    try:
        payload = json.loads(payload)
    except json.JSONDecodeError:
        payload = {}
        
    if 'report' in payload and 'battery' in payload['report']:
        battery_percent = payload['report']['battery']['percent']


async def main():
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)  # ThinQApi 인스턴스 생성
        device_list = await thinq_api.async_get_device_list()
        print("device_list : %s", device_list)
        device_id = device_list[0].get("deviceId")



        profile = await thinq_api.async_get_device_profile(device_id=device_id)
        print("profile : %s", profile)
        status = await thinq_api.async_get_device_status(device_id=device_id)
        print("status : %s", status)

        await thinq_api.async_delete_push_subscribe(device_id=device_id)
        await thinq_api.async_delete_event_subscribe(device_id=device_id)


        response = await thinq_api.async_post_push_subscribe(device_id=device_id)
        print("push subscribe : %s", response)
        response = await thinq_api.async_post_event_subscribe(device_id=device_id)
        print("event subscribe : %s", response)

        mqtt_client = ThinQMQTTClient(
            thinq_api=thinq_api,
            client_id=client_id,
            on_message_received       = on_message_received,
            on_connection_interrupted = lambda **kwargs: print("Connection Interrupted"),
            on_connection_success     = lambda **kwargs: print("Connection Success"),
            on_connection_failure     = lambda **kwargs: print("Connection Failure"),
            on_connection_closed      = lambda **kwargs: print("Connection Closed")
        )

        await mqtt_client.async_init()
        await mqtt_client.async_prepare_mqtt()
        await mqtt_client.async_connect_mqtt()
     



async def async_start_thinq_host():
    global battery_percent
    async with ClientSession() as session:
        thinq_api = ThinQApi(session=session, access_token='', country_code='KR', client_id=client_id)  # ThinQApi 인스턴스 생성
        device_list = await thinq_api.async_get_device_list()
        print("device_list : %s", device_list)
        device_id = device_list[0].get("deviceId")



        profile = await thinq_api.async_get_device_profile(device_id=device_id)
        print("profile : %s", profile)
        status = await thinq_api.async_get_device_status(device_id=device_id)
        print("status : %s", status)

        battery_percent = status['battery']['percent']

        await thinq_api.async_delete_push_subscribe(device_id=device_id)
        await thinq_api.async_delete_event_subscribe(device_id=device_id)


        response = await thinq_api.async_post_push_subscribe(device_id=device_id)
        print("push subscribe : %s", response)
        response = await thinq_api.async_post_event_subscribe(device_id=device_id)
        print("event subscribe : %s", response)

        mqtt_client = ThinQMQTTClient(
            thinq_api=thinq_api,
            client_id=client_id,
            on_message_received       = on_message_received,
            on_connection_interrupted = lambda **kwargs : print("Connection Interrupted"),
            on_connection_success     = lambda **kwargs : print("Connection Success"),
            on_connection_failure     = lambda **kwargs : print("Connection Failure"),
            on_connection_closed      = lambda **kwargs : print("Connection Closed")
        )

        await mqtt_client.async_init()
        await mqtt_client.async_prepare_mqtt()
        await mqtt_client.async_connect_mqtt()

        while mqtt_client.is_connected:
            await asyncio.sleep(1)  # Prevents busy waiting


def start_thinq_host_thread():
    mqtt_thread = threading.Thread(target=lambda : asyncio.run(async_start_thinq_host()))
    mqtt_thread.start()
    
