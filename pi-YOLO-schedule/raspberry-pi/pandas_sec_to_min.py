import pandas as pd
import numpy as np

def sec_to_min(df):
    # CSV 파일 읽기
    df = pd.read_csv('aggregated_data_second.csv')  # csv 파일 읽기

    # timestamp를 datetime 형식으로 변환
    df['second'] = pd.to_datetime(df['second'])

    # None 값을 0으로 대체
    df.fillna(0, inplace=True)

    # 분 단위로 집계하기 위해 '분'으로 그룹화
    df['minute'] = df['second'].dt.floor('T')
    grouped_minutes = df.groupby('minute').agg(
        class_count=('class_count', 'sum'),  # 분 단위에서 class_count 합계
        data_count=('data_count', 'sum'),  # 분 단위에서 data_count 합계
        confidence_mean=('confidence_mean', 'mean'),
        x1_mean=('x1_mean', 'mean'),
        y1_mean=('y1_mean', 'mean'),
        x2_mean=('x2_mean', 'mean'),
        y2_mean=('y2_mean', 'mean'),
        brightness_mean=('brightness_mean', 'mean'),
        center_x_mean=('center_x', 'mean'),  # center_x 평균
        center_y_mean=('center_y', 'mean'),  # center_y 평균
        center_x_values=('center_x', list),  # center_x 값 리스트
        center_y_values=('center_y', list),   # center_y 값 리스트
        recognition_rate=('recognition_rate', 'mean'),
        presence_count=('recognition_decision', lambda x: (x == '존재').sum()),  # '존재' 개수
        absence_count=('recognition_decision', lambda x: (x == '부재').sum()),   # '부재' 개수
        confidence_count=('confidence_mean', lambda x: (x > 0).sum())
    ).reset_index()

    # presence_decision 계산
    grouped_minutes['presence_decision'] = np.where(
        grouped_minutes['presence_count'] >= grouped_minutes['absence_count'], '존재', '부재'
    )

    # center_x_min, center_y_min, center_x_max, center_y_max 계산
    def calculate_center_values(row):
        if row['confidence_count'] == 1:
            # confidence_mean이 0이 아닌 값이 하나만 존재하는 경우
            center_x_min = row['center_x_values'][0]
            center_x_max = row['center_x_values'][0]
            center_y_min = row['center_y_values'][0]
            center_y_max = row['center_y_values'][0]
            movement_decision = '움직임 판단 불가'
        else:
            # confidence_mean이 0이 아닌 값이 2개 이상인 경우
            center_x_min = min([x for x in row['center_x_values'] if x > 0], default=None)  # NaN보다 큰 값 중 최소
            center_x_max = max(row['center_x_values'])  # 최대값
            center_y_min = min([y for y in row['center_y_values'] if y > 0], default=None)  # NaN보다 큰 값 중 최소
            center_y_max = max(row['center_y_values'])  # 최대값
            movement_decision = None  # 초기화

        return pd.Series([center_x_min, center_y_min, center_x_max, center_y_max, movement_decision])

    # center_x, center_y 값 계산
    grouped_minutes[['center_x_min', 'center_y_min', 'center_x_max', 'center_y_max', 'movement_decision']] = grouped_minutes.apply(calculate_center_values, axis=1)

    # NaN 값 처리: center_xy_dist 계산
    grouped_minutes['center_xy_dist'] = np.where(
        grouped_minutes['center_x_min'].isna() | grouped_minutes['center_y_min'].isna(),
        None,
        np.sqrt(
            (grouped_minutes['center_x_max'].astype(float) - grouped_minutes['center_x_min'].astype(float))**2 + 
            (grouped_minutes['center_y_max'].astype(float) - grouped_minutes['center_y_min'].astype(float))**2
        )
    )

    # 동적/정적 판단
    center_distance_threshold = 150
    grouped_minutes['movement_decision'] = grouped_minutes.apply(
        lambda row: '움직임 판단 불가' if row['movement_decision'] == '움직임 판단 불가' else (
            '동적' if row['center_xy_dist'] is not None and row['center_xy_dist'] > center_distance_threshold else '정적'
        ),
        axis=1
    )


    # 최종 데이터프레임
    final_df = grouped_minutes[['minute', 'class_count', 'data_count', 'confidence_mean', 'x1_mean', 'y1_mean', 'x2_mean', 'y2_mean', 'brightness_mean', 'recognition_rate', 'presence_count', 'absence_count', 'confidence_count', 'presence_decision', 'center_x_mean', 'center_y_mean', 'center_x_min', 'center_y_min', 'center_x_max', 'center_y_max', 'center_xy_dist', 'movement_decision']]

    # CSV 파일로 저장
    final_df.to_csv('aggregated_data_minute.csv', index=False)

    print(final_df)
