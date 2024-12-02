import os
import time
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd
import pandas_ms_to_sec
import pandas_sec_to_min
import pandas_schedule_new
import schedule_merge

class MultiFileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_paths):
        self.file_paths = file_paths
        #self.last_hashes = {file_path: self.get_file_hash(file_path) for file_path in file_paths}

    # def get_file_hash(self, file_path):
    #     """파일의 해시값을 계산합니다."""
    #     try:
    #         with open(file_path, 'rb') as f:
    #             file_hash = hashlib.sha256()
    #             while True:
    #                 chunk = f.read(8192)
    #                 if not chunk:
    #                     break
    #                 file_hash.update(chunk)
    #             return file_hash.hexdigest()
    #     except FileNotFoundError:
    #         return None

    def on_modified(self, event):
        """파일이 수정되었을 때 호출됩니다."""
        print(f"파일 수정이 감지되었습니다. : {event.src_path}")
        if event.src_path in self.file_paths:
            #print(f"Modified event detected: {event.src_path}")  # 감지 로그 추가
            self.file_changed(event.src_path)

    def file_changed(self, file_path):
        """파일이 변경되었을 때 실행할 함수입니다."""
        #import pdb
        #pdb.set_trace()
        while True:
            try:
                df = pd.read_csv(file_path)  # CSV 파일을 DataFrame으로 읽기
                break  # 파일 읽기가 성공하면 루프 탈출
            except PermissionError:
                print(f"PermissionError: {file_path} is not ready yet, retrying...")
                time.sleep(1)  # 1초 대기 후 재시도
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                return  # 다른 오류가 발생하면 메서드 종료
            
        if file_path == os.path.abspath('combined_file.csv'):
            self.handle_combined_file(df)
        elif file_path == os.path.abspath('aggregated_data_second.csv'):
            self.handle_aggregated_data_second(df)
        elif file_path == os.path.abspath('aggregated_data_minute.csv'):
            self.handle_aggregated_data_minute(df)
        elif file_path == os.path.abspath('schedule.csv'):
            self.handle_schedule(df)

    def handle_combined_file(self, df):
        print("combined_file.csv 파일이 변경되었습니다. 작업을 수행합니다.")
        pandas_ms_to_sec.ms_to_sec(df)
        print(df.head())  # DataFrame의 첫 5행 출력

    def handle_aggregated_data_second(self, df):
        print("aggregated_data_second.csv 파일이 변경되었습니다. 작업을 수행합니다.")
        pandas_sec_to_min.sec_to_min(df)
        print(df.head())  # DataFrame의 첫 5행 출력

    def handle_aggregated_data_minute(self, df):
        print("aggregated_data_minute.csv 파일이 변경되었습니다. 작업을 수행합니다.")
        pandas_schedule_new.min_to_schedule(df)
        print(df.head())  # DataFrame의 첫 5행 출력

    def handle_schedule(self, df):
        print("schedule.csv 파일이 변경되었습니다. 작업을 수행합니다.")
        schedule_history = pd.read_csv(f'schedule_history/schedule.csv')
        schedule_merge.merge_schedule(schedule_history, df)

        

def monitor_files(file_paths):
    event_handler = MultiFileChangeHandler(file_paths)
    observer = Observer()
    
    for file_path in file_paths:
        directory = os.path.dirname(file_path)
        observer.schedule(event_handler, path=directory, recursive=False)
    observer.start()
    print(f"{', '.join(file_paths)} 파일 감시 중...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    current_directory = os.getcwd()  # 현재 작업 디렉토리
    files_to_monitor = [
        os.path.join(current_directory, 'combined_file.csv'),
        os.path.join(current_directory, 'aggregated_data_second.csv'),
        os.path.join(current_directory, 'aggregated_data_minute.csv'),
        os.path.join(current_directory, 'schedule.csv')
    ]
    monitor_files(files_to_monitor)
