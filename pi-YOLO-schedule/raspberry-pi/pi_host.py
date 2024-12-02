import socket
import struct
import cv2
import numpy as np
import pickle
import threading
import pandas as pd
from datetime import datetime

total_rows = 0
saved_rows = 0 
lock = threading.Lock()  # 스레드 안전을 위한 잠금

def receive_frames(host, port):
    # Create a socket connection for image frames
    frame_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    frame_socket.connect((host, port))

    data = b""
    payload_size = struct.calcsize(">I")

    try:
        while True:
            # Retrieve message size
            while len(data) < payload_size:
                packet = frame_socket.recv(4096)
                if not packet:
                    break
                data += packet
            if not data:
                break
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">I", packed_msg_size)[0]

            # Retrieve all data based on message size
            while len(data) < msg_size:
                packet = frame_socket.recv(4096)
                if not packet:
                    break
                data += packet
            frame_data = data[:msg_size]
            data = data[msg_size:]

            # Decode image
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            image = cv2.imdecode(frame, cv2.IMREAD_COLOR)

            if image is None:
                print("Failed to decode image")
                continue

            # Display image
            cv2.imshow('Received Frame', image)
            if cv2.waitKey(1) == ord('q'):
                break
    except Exception as e:
        print(f"Error receiving frames: {e}")
    finally:
        frame_socket.close()
        cv2.destroyAllWindows()

def save_dataframe(df):
    # DataFrame을 CSV 파일로 저장
    df.to_csv('received_data.csv', mode='w', header=False, index=False)

def receive_dataframes(host, port):
    # Create a socket connection for DataFrames
    global total_rows, saved_rows
    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_socket.connect((host, port))

    data = b""
    payload_size = struct.calcsize(">I")

    try:
        while True:
            # Retrieve message size
            while len(data) < payload_size:
                packet = data_socket.recv(4096)
                if not packet:
                    break
                data += packet
            if not data:
                break
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">I", packed_msg_size)[0]

            # Retrieve all data based on message size
            while len(data) < msg_size:
                packet = data_socket.recv(4096)
                if not packet:
                    break
                data += packet
            df_data = data[:msg_size]
            data = data[msg_size:]

            # Deserialize DataFrame
            df = pickle.loads(df_data)

            if isinstance(df, pd.DataFrame):
                # Print DataFrame
                #print(df)
                with lock:
                    total_rows += df.shape[0]  # 총 행 수 업데이트
                    print(f"Received DataFrame with {df.shape[0]} rows.")

                
                    save_dataframe(df)
                
            else:
                print("Received data is not a DataFrame")
    except Exception as e:
        print(f"Error receiving DataFrames: {e}")
    finally:
        data_socket.close()

def receive_csv(host, port):
    csv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    csv_socket.connect((host, port))

    data = b""
    payload_size = struct.calcsize(">I")

    try:
        while True:
            # Retrieve message size
            while len(data) < payload_size:
                packet = csv_socket.recv(4096)
                if not packet:
                    break
                data += packet
            if not data:
                break
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">I", packed_msg_size)[0]

            # Retrieve all data based on message size
            while len(data) < msg_size:
                packet = csv_socket.recv(4096)
                if not packet:
                    break
                data += packet
            csv_data = data[:msg_size]
            data = data[msg_size:]


            current_timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            csv_file_name = f"received/{current_timestamp}.csv"
            

            # Save received CSV data to a file
            with open(csv_file_name, 'wb') as f:
                f.write(csv_data)
            print(f"CSV file received and saved as '{csv_file_name}'")
    except Exception as e:
        print(f"Error receiving CSV: {e}")
    finally:
        csv_socket.close()


if __name__ == "__main__":
    host = ''  
    frame_port =   
    data_port =    
    csv_port = 

    # Create threads for receiving frames and data
    frame_thread = threading.Thread(target=receive_frames, args=(host, frame_port))
    data_thread = threading.Thread(target=receive_dataframes, args=(host, data_port))
    csv_thread = threading.Thread(target=receive_csv, args=(host, csv_port))

    frame_thread.start()
    data_thread.start()
    csv_thread.start()

    frame_thread.join()
    data_thread.join()
    csv_thread.join()
