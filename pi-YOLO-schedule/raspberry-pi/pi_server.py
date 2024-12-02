#!/usr/bin/env python3

from flask import Flask, Response, render_template, jsonify, request, abort
import cv2
from picamera2 import Picamera2
import libcamera
import time
import threading
import pandas as pd
import os

import asyncio
import thinq
import pytz
from datetime import datetime, timedelta

#battery_percent = 0



CAM_X = 640
CAM_Y = 480


CAM_HFLIP = False
CAM_VFLIP = False

MAX_FPS = 30


WEB_PORT = 8000
app = Flask(__name__)


class MgtData(object):
    stop_tasks = False            
    frame1_has_new_data = False   
    lock1 = False                 
    frame2_has_new_data = False   
    lock2 = False

    img_buffer1 = None            
    img_buffer2 = None            
    encoded_frame1 = None         
    encoded_frame2 = None         

    
    def frame1_new_data():
        return (MgtData.frame1_has_new_data and not MgtData.lock1)

    
    def frame2_new_data():
        return (MgtData.frame2_has_new_data and not MgtData.lock2)



@app.route('/mjpg')
def video_feed():
    generated_data  = gen()
    if (generated_data):
        response = Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame') 
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    return None


def gen():
    while not MgtData.stop_tasks:  
        while (not (MgtData.frame1_new_data() or MgtData.frame2_new_data())):
            time.sleep (0.01) 

        frame = get_frame()
        
        yield (b'--frame\r\n'
                b'Content-Type:image/jpeg\r\n'
                b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
                b'\r\n' + frame + b'\r\n')


def get_frame():
    encoded_frame = None
    if (MgtData.frame1_new_data() or MgtData.frame2_new_data()):
        if (MgtData.frame1_new_data ()):
            encoded_frame = MgtData.encoded_frame1
            MgtData.frame1_has_new_data = False
        elif (MgtData.frame2_new_data ()):
            encoded_frame = MgtData.encoded_frame2
            MgtData.frame2_has_new_data = False
    else:
        print ("Duplicate frame")

    return encoded_frame





def start_webserver():
    try:
        app.run(host='0.0.0.0', port=WEB_PORT, threaded=True, debug=False)
    except Exception as e:
        print(e)


def encode1():
    newEncFrame = cv2.imencode('.jpg', MgtData.img_buffer1)[1].tobytes()
    MgtData.encoded_frame1 = newEncFrame
    MgtData.frame1_has_new_data = True
    MgtData.lock1 = False


def encode2():
    MgtData.lock2 = True
    MgtData.frame2_has_new_data = True
    newEncFrame = cv2.imencode('.jpg', MgtData.img_buffer2)[1].tobytes()
    MgtData.encoded_frame2 = newEncFrame
    MgtData.lock2 = False



def run_camera():
    # init picamera
    picam2 = Picamera2()

    preview_config = picam2.preview_configuration
    preview_config.size = (CAM_X, CAM_Y)
    preview_config.format = 'RGB888'
    preview_config.transform = libcamera.Transform(hflip=CAM_HFLIP, vflip=CAM_VFLIP)
    preview_config.colour_space = libcamera.ColorSpace.Sycc()
    preview_config.buffer_count = 4 
    preview_config.queue = True
    preview_config.controls = {'FrameRate': MAX_FPS and MAX_FPS or 100}

    try:
        picam2.start()

    except Exception as e:
        print(e)
        print("Is the camera connected correctly?\nYou can use the \"libcamea-hello\" or \"rpicam-hello\" to test the camera.")
        exit(1)
    
    fps = 0
    start_time = 0
    framecount = 0
    try:
        start_time = time.time()
        while (not MgtData.stop_tasks):
            if (not (MgtData.frame1_new_data() and MgtData.frame2_new_data())):

                
                my_img = picam2.capture_array()

                
                framecount += 1
                elapsed_time = float(time.time() - start_time)
                if (elapsed_time > 1):
                    fps = round(framecount/elapsed_time, 1)
                    framecount = 0
                    start_time = time.time()
                    print ("FPS: ", fps)

                
                if (not MgtData.frame1_new_data()):
                    MgtData.img_buffer1 = my_img
                    MgtData.frame1_has_new_data = True
                    MgtData.lock1 = True
                    encode_thread1 = threading.Thread(target=encode1, name="encode1")
                    encode_thread1.start()
                elif (not MgtData.frame2_new_data()):
                    MgtData.img_buffer2 = my_img
                    MgtData.frame2_has_new_data = True
                    MgtData.lock2 = True
                    encode_thread2 = threading.Thread(target=encode2, name="encode1")
                    encode_thread2.start()
            time.sleep (0.0005) 
            
    except KeyboardInterrupt as e:
        print(e)
        MgtData.stop_tasks
    finally:
        picam2.close()
        cv2.destroyAllWindows()



def streamon():
    camera_thread = threading.Thread(target= run_camera, name="camera_streamon")
    camera_thread.daemon = False
    camera_thread.start()

    if camera_thread != None and camera_thread.is_alive():
        print('Starting web streaming ...')
        flask_thread = threading.Thread(name='flask_thread',target=start_webserver)
        flask_thread.daemon = True
        flask_thread.start()
    else:
        print('Error starting the stream')

    while not MgtData.stop_tasks:
        time.sleep (25) 

@app.route('/battery-status')
def battery_status():
    
    return jsonify(battery=thinq.battery_percent)

@app.route('/control/<action>', methods=['POST'])
def control_robot(action):
    if action == 'start':
        asyncio.run(thinq.devices_control(payload=thinq.payload_op_start))
        return jsonify(status='success', message='로봇이 시작되었습니다.')
    elif action == 'restart':
        asyncio.run(thinq.devices_control(payload=thinq.payload_op_resume))
        return jsonify(status='success', message='로봇이 재시작되었습니다.')
    elif action == 'pause':
        asyncio.run(thinq.devices_control(payload=thinq.payload_op_pause))
        return jsonify(status='success', message='로봇이 일시 정지되었습니다.')
    elif action == 'return':
        asyncio.run(thinq.devices_control(payload=thinq.payload_op_homing))
        return jsonify(status='success', message='로봇이 충전대로 복귀합니다.')
    else:
        return jsonify(status='error', message='유효하지 않은 작업입니다.')

@app.route('/')
def main():

    return render_template('main.html')

def read_csv_data():
    file_path = 'schedule_history/schedule.csv'
    df = pd.read_csv(file_path)
    
    
    seoul_tz = pytz.timezone('Asia/Seoul')
    df['timestamp1'] = pd.to_datetime(df['timestamp1']).dt.tz_localize(seoul_tz)
    df['timestamp2'] = pd.to_datetime(df['timestamp2']).dt.tz_localize(seoul_tz)
    
    
    schedule_data = {i: [] for i in range(7)}  # 0(월) ~ 6(일)
    
    for _, row in df.iterrows():
        start = row['timestamp1']
        end = row['timestamp2']
        day_of_week = start.weekday()
        
        schedule_data[day_of_week].append({
            'timestamp1': start.strftime('%H:%M'),
            'timestamp2': end.strftime('%H:%M'),
            'running_time': row['running_time']
        })
    
    return schedule_data

@app.route('/schedule')
def schedule():
    try:
        data = read_csv_data()
        now = datetime.now(pytz.timezone('Asia/Seoul'))
        return render_template('schedule.html', data=data, current_time=now.isoformat())
    except Exception as e:
        print(f"Error: {str(e)}")
        return "스케줄 데이터를 불러오는 중 오류가 발생했습니다.", 500

def schedule_action(action, delay=0):
    def run_action():
        if action == 'start':
            asyncio.run(thinq.devices_control(payload=thinq.payload_op_start))
        elif action == 'return':
            asyncio.run(thinq.devices_control(payload=thinq.payload_op_homing))

    if delay > 0:
        timer = threading.Timer(delay, run_action)
        timer.start()
    else:
        run_action()

@app.route('/reserve_day', methods=['POST'])
def reserve_day():
    day = request.json.get('day')
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    current_day = now.weekday()
    current_time = now.time()
    
    data = read_csv_data()
    schedules = data[day]
    
    if day == current_day:
        
        schedules = [s for s in schedules if datetime.strptime(s['timestamp1'], '%H:%M').time() > current_time]
        if not schedules:
            return jsonify(status='error', message='오늘 예약할 수 있는 스케줄이 없습니다.')
    elif day < current_day:
        
        now += timedelta(days=7 - current_day + day)
    else:
        
        now += timedelta(days=day - current_day)
    
    if not schedules:
        return jsonify(status='error', message='오늘 예약할 수 있는 스케줄이 없습니다.')
    
    
    for schedule in schedules:
        start_time = pytz.timezone('Asia/Seoul').localize(datetime.combine(now.date(), datetime.strptime(schedule['timestamp1'], '%H:%M').time()))
        end_time = pytz.timezone('Asia/Seoul').localize(datetime.combine(now.date(), datetime.strptime(schedule['timestamp2'], '%H:%M').time()))

        # Calculate delays
        start_delay = (start_time - now).total_seconds()
        end_delay = (end_time - now).total_seconds()
        
        # Schedule start action
        schedule_action('start', max(0, start_delay))
        
        # Schedule return action
        schedule_action('return', max(0, end_delay))
    
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    return jsonify(status='success', message=f'{now.strftime("%Y-%m-%d")} {day_names[day]}요일의 스케줄이 예약되었습니다.')

@app.route('/reserve_schedule', methods=['POST'])
def reserve_schedule():
    schedule = request.json
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    current_day = now.weekday()
    current_time = now.time()
    
    start_time = datetime.strptime(schedule['timestamp1'], '%H:%M').time()
    end_time = datetime.strptime(schedule['timestamp2'], '%H:%M').time()
    
    if current_day == int(schedule['day']):
        if current_time > end_time or (current_time > start_time and current_time < end_time):
            # Schedule for next week
            now += timedelta(days=7)
    elif int(schedule['day']) < current_day:
        # Schedule for next week
        now += timedelta(days=7 - current_day + int(schedule['day']))
    else:
        # Schedule for this week
        now += timedelta(days=int(schedule['day']) - current_day)
    
    timezone = pytz.timezone('Asia/Seoul')
    start_datetime = timezone.localize(datetime.combine(now.date(), start_time))
    end_datetime = timezone.localize(datetime.combine(now.date(), end_time))
    
    # Calculate delays
    start_delay = (start_datetime - now).total_seconds()
    end_delay = (end_datetime - now).total_seconds()
    
    # Schedule start action
    schedule_action('start', max(0, start_delay))
    
    # Schedule return action
    schedule_action('return', max(0, end_delay))
    
    return jsonify(status='success', message=f'{start_datetime.strftime("%Y-%m-%d %H:%M")}부터 {end_datetime.strftime("%H:%M")}까지의 스케줄이 예약되었습니다.')


@app.route('/streaming')
def streaming_page():
    return render_template('streaming.html')

@app.before_first_request
def mqtt_run():
    thinq.start_thinq_host_thread()

@app.before_request
def limit_remote_addr():
    if request.remote_addr == '18.170.66.55':
        abort(403)


if __name__ == "__main__":
    try:
        streamon()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    finally:
        print ("Closing...")
        MgtData.stop_tasks = True
