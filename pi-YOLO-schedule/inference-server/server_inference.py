import time
import cv2
from ultralytics import YOLO
import pandas as pd
from datetime import datetime
import pytz
import sys
import io
import socket
import struct
import threading
import pickle

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class VideoProcessor:
    def __init__(self, model_path, stream_url, target_classes):
        # Load the YOLO model
        self.model = YOLO(model_path)
        # Set up video capture
        self.cap = cv2.VideoCapture(stream_url)
        if not self.cap.isOpened():
            print("Error: Could not open video stream.")
            exit()
        # Initialize variables
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.results_df = pd.DataFrame(columns=[
            "timestamp", "class_id", "confidence", "x1", "y1", "x2", "y2", "brightness"])
        self.target_classes = target_classes
        # Set timezone
        self.timezone = pytz.timezone('Asia/Seoul')

    def calculate_brightness(self, image):
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        brightness = hsv_image[:, :, 2].mean()
        return brightness

    def process_frame(self):
        # Read frame
        ret, image = self.cap.read()
        if not ret:
            print("Error: Could not read frame from stream.")
            return None, None
        # Process with YOLO model
        results = self.model(image)
        current_timestamp = datetime.now(
            self.timezone).strftime("%Y-%m-%d-%H-%M-%S-%f")[:-3]
        brightness = self.calculate_brightness(image)
        detected = False

        for result in results:
            if result.boxes.data.size(0) > 0:
                boxes = result.boxes
                for box in boxes:
                    confidence = box.conf[0].item()
                    class_id = int(box.cls[0].item())
                    class_name = self.model.names[class_id]
                    if class_name in self.target_classes and confidence > 0.2:
                        detected = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = f"{class_name} {confidence:.2f}"
                        cv2.rectangle(image, (x1, y1), (x2, y2),
                                      (0, 255, 0), 2)
                        cv2.putText(image, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        self.results_df = self.results_df.append({
                            "timestamp": current_timestamp,
                            "class_id": class_id,
                            "confidence": confidence,
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "brightness": brightness
                        }, ignore_index=True)
        if not detected:
            # No detections; record timestamp and brightness
            self.results_df = self.results_df.append({
                "timestamp": current_timestamp,
                "class_id": None,
                "confidence": None,
                "x1": None,
                "y1": None,
                "x2": None,
                "y2": None,
                "brightness": brightness
            }, ignore_index=True)
        # Encode image to JPEG
        result, encoded_image = cv2.imencode('.jpg', image)
        if not result:
            print("Error: Failed to encode image.")
            return None, None
        frame_data = encoded_image.tobytes()
        return frame_data, self.results_df.copy()

    def reset_dataframe(self):
        self.results_df = pd.DataFrame(columns=[
            "timestamp", "class_id", "confidence", "x1", "y1", "x2", "y2", "brightness"])

    def run(self, frame_sender, data_sender, csv_sender):
        try:
            while True:
                frame_data, df_data = self.process_frame()
                if frame_data is None:
                    continue
                # Send frame data
                if frame_sender.clients:
                    frame_sender.send_frame_to_clients(frame_data)
                # Send DataFrame data
                if data_sender.clients:
                    data_sender.send_dataframe_to_clients(df_data)
                # Save DataFrame when it reaches a certain length
                if len(self.results_df) >= 200:
                    current_timestamp = datetime.now(
                        self.timezone).strftime("%Y-%m-%d-%H-%M-%S-%f")[:-3]
                    csv_file_path = f"{current_timestamp}.csv"
                    self.results_df.to_csv(csv_file_path, index=False)
                    csv_sender.send_csv_to_clients(csv_file_path)
                    self.reset_dataframe()
                # FPS calculation
                self.frame_count += 1
                if time.time() - self.fps_start_time >= 1.0:
                    elapsed_time = time.time() - self.fps_start_time
                    print(
                        f"Frames per second: {self.frame_count / elapsed_time:.2f}")
                    self.frame_count = 0
                    self.fps_start_time = time.time()
        finally:
            self.cap.release()
            # Save any remaining results
            self.results_df.to_csv("inference_results.csv", index=False)
            csv_sender.send_csv_to_clients("inference_results.csv")
            print("Inference results saved to inference_results.csv")


class ClientHandler:
    def __init__(self, host, port):
        self.clients = []
        self.host = host
        self.port = port
        self.server_socket = None
        self.accept_thread = None

    def start_server(self):
        # Set up server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")
        # Start accepting clients
        self.accept_thread = threading.Thread(target=self.accept_clients)
        self.accept_thread.daemon = True
        self.accept_thread.start()

    def accept_clients(self):
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"Client connected from: {client_address}")
            self.clients.append(client_socket)

    def send_to_clients(self, data):
        # Placeholder method to be overridden
        pass


class FrameSender(ClientHandler):
    def send_frame_to_clients(self, frame_data):
        for client in self.clients[:]:
            try:
                data_length = len(frame_data)
                client.sendall(struct.pack('>I', data_length) + frame_data)
            except Exception as e:
                print(f"Failed to send frame to client: {e}")
                self.clients.remove(client)
                client.close()


class DataSender(ClientHandler):
    def send_dataframe_to_clients(self, df):
        # Serialize DataFrame
        df_bytes = pickle.dumps(df)
        for client in self.clients[:]:
            try:
                data_length = len(df_bytes)
                client.sendall(struct.pack('>I', data_length) + df_bytes)
            except Exception as e:
                print(f"Failed to send data to client: {e}")
                self.clients.remove(client)
                client.close()
    def send_csv_to_clients(self, file_path):
        with open(file_path, 'rb') as f:
            csv_data = f.read()
            for client in self.clients[:]:
                try:
                    data_length = len(csv_data)
                    client.sendall(struct.pack('>I', data_length) + csv_data)
                except Exception as e:
                    print(f"Failed to send CSV to client: {e}")
                    self.clients.remove(client)
                    client.close() 


def main():
    # Video stream URL
    username = ""
    password = ""
    ip_address = ""
    port = ""
    url = f"http://{ip_address}:{port}/mjpg"

    # Target classes
    target_classes = ["person", "cat", "dog"]

    # Initialize VideoProcessor
    video_processor = VideoProcessor(
        model_path="yolov8n.pt", stream_url=url, target_classes=target_classes)

    # Initialize servers with separate ports
    frame_server = FrameSender(host='0.0.0.0', port=20)  # Port for frames
    data_server = DataSender(host='0.0.0.0', port=23)    # Port for data
    csv_server = DataSender(host='0.0.0.0', port=24)

    # Start servers
    frame_server.start_server()
    data_server.start_server()
    csv_server.start_server()

    # Run video processing
    video_processor.run(frame_server, data_server, csv_server)


if __name__ == "__main__":
    main()
