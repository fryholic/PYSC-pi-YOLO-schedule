import os
import time
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import combine_csv

class MyHandler(FileSystemEventHandler):
    def __init__(self, folder_to_watch):
        self.folder_to_watch = folder_to_watch
        self.initial_file_name = None
        self.last_timestamp_file = None
        self.check_initial_files()

    def check_initial_files(self):
        # 폴더에 파일이 없는지 확인
        if not os.listdir(self.folder_to_watch):
            print("폴더에 파일이 없습니다. 파일이 생성되기를 기다립니다.")
        else:
            print("폴더에 기존 파일이 존재합니다.")

    def on_created(self, event):
        if not event.is_directory:
            print(f"새 파일 생성됨: {event.src_path}")  # 디버깅을 위한 출력
            file_name, file_extension = os.path.splitext(os.path.basename(event.src_path))
            if self.initial_file_name is None:
                self.initial_file_name = file_name
                print(f"첫 번째 생성된 파일: {self.initial_file_name}")
            else:
                self.check_and_process(file_name)

    def check_and_process(self, file_name):
        
        # 첫 번째 파일명으로부터 7일이 지났는지 확인
        initial_time = datetime.datetime.strptime(self.initial_file_name, "%Y-%m-%d-%H-%M-%S")
        current_time = datetime.datetime.strptime(file_name, "%Y-%m-%d-%H-%M-%S")

        # 7일 후
        seven_days_later = initial_time + datetime.timedelta(days=7)

        if current_time >= seven_days_later:
            print("7일이 지난 파일이 감지되었습니다.")
            if os.listdir(self.folder_to_watch):
                combine_csv.combine_csv() # 축적된 csv 파일들 합치기
               
                # 7일이 지난 파일을 제외한 나머지 파일 삭제
                for f in os.listdir(self.folder_to_watch):
                    # 7일이 지난 파일과 비교
                    try:
                        file_time = datetime.datetime.strptime(f, "%Y-%m-%d-%H-%M-%S.csv")  # 확장자 포함
                    except ValueError:
                        continue  # 형식 오류 발생 시 건너뛰기

                    if file_time < seven_days_later:
                        os.remove(os.path.join(self.folder_to_watch, f))
                        print(f"삭제된 파일: {f}")

                # 마지막으로 7일이 지난 파일명을 저장
                print(f"저장된 7일 지난 파일명: {self.last_timestamp_file}")
                
                self.initial_file_name = file_name
                self.last_timestamp_file = None
                

def start_watching(folder_to_watch):
    event_handler = MyHandler(folder_to_watch)
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()
    print(f"{folder_to_watch} 폴더를 감시합니다.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    folder_path = "received"  # 감시할 폴더 경로를 입력하세요
    start_watching(folder_path)
