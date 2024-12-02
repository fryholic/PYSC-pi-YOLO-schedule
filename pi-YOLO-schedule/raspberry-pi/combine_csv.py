import pandas as pd
import glob
import os

def combine_csv():
    file_path = 'received/*.csv'
    folder_path = 'received'
    if os.listdir(folder_path):
    # CSV 파일이 저장된 디렉토리의 경로
        

        # 모든 CSV 파일을 읽어와서 리스트에 저장
        all_files = glob.glob(file_path)

        # 각 CSV 파일을 읽고 리스트로 저장
        dataframes = [pd.read_csv(file) for file in all_files]

        # 모든 데이터프레임을 하나로 합치기
        combined_df = pd.concat(dataframes, ignore_index=True)

        # 결과를 새로운 CSV 파일로 저장
        combined_df.to_csv('combined_file.csv', index=False)
