import pandas as pd

def ms_to_sec(df):
    # CSV 파일 읽기
    df = pd.read_csv('combined_file.csv')  # csv 파일 읽기

    # timestamp를 datetime 형식으로 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d-%H-%M-%S-%f')

    # 밀리초를 초 단위로 집계하기 위해 '초'로 그룹화
    df['second'] = df['timestamp'].dt.floor('S')
    grouped = df.groupby('second').agg(
        class_count=('class_id', lambda x: x.notna().sum()),
        data_count=('timestamp', 'count'),
        confidence_mean=('confidence', 'mean'),
        x1_mean=('x1', 'mean'),
        y1_mean=('y1', 'mean'),
        x2_mean=('x2', 'mean'),
        y2_mean=('y2', 'mean'),
        brightness_mean=('brightness', 'mean'),
        count=('timestamp', 'count')
    ).reset_index()

    # 인식률 계산
    grouped['recognition_rate'] = grouped['class_count'] / grouped['count']

    # 평균 바운딩 박스 좌표 계산
    #grouped['bounding_box_mean'] = grouped[['x1_mean', 'y1_mean', 'x2_mean', 'y2_mean']].mean(axis=1)

    # 바운딩 박스의 중심 좌표 계산
    grouped['center_x'] = (grouped['x1_mean'] + grouped['x2_mean']) / 2
    grouped['center_y'] = (grouped['y1_mean'] + grouped['y2_mean']) / 2

    # 인식 판단
    threshold = 0.3
    grouped['recognition_decision'] = grouped['recognition_rate'].apply(lambda x: '존재' if x > threshold else '부재')

    # 최종 데이터프레임
    final_df = grouped[['second', 'data_count', 'class_count', 'confidence_mean', 'x1_mean', 'y1_mean', 'x2_mean', 'y2_mean', 'center_x', 'center_y', 'brightness_mean', 'recognition_rate', 'recognition_decision']]

    # CSV 파일로 저장
    final_df.to_csv('aggregated_data_second.csv', index=False)

#print(final_df)
