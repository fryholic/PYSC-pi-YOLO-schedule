import pandas as pd


def min_to_schedule(df):
    # CSV 파일에서 데이터프레임 읽기
    df = pd.read_csv('aggregated_data_minute.csv')  

    # 'minute' 열을 datetime 형식으로 변환
    df['minute'] = pd.to_datetime(df['minute'])

    # 결과를 저장할 리스트
    results = []

    # 상태 변수 초기화
    last_static_time = None

    # 데이터프레임 순회
    for index, row in df.iterrows():
        # 'movement_decision'이 '정적'인 경우
        if row['movement_decision'] in ['정적', '움직임 판단 불가']:
            if last_static_time is None:
                last_static_time = row['minute']
        # 'movement_decision'이 '동적'인 경우
        elif row['movement_decision'] == '동적' and last_static_time is not None:
            time_difference = row['minute'] - last_static_time
            if time_difference.total_seconds() >= 1800:  # 30분 이상
                results.append((last_static_time, row['minute'], time_difference))
            last_static_time = None  # '동적' 후에는 '정적' 상태를 기다림

    result_df = pd.DataFrame(results, columns=['timestamp1', 'timestamp2', 'running_time'])

    # running_time을 timedelta 형식으로 변환하여 문자열로 표시
    result_df['running_time'] = result_df['running_time'].dt.total_seconds() / 60  # 분 단위로 변환

    # 15분 이하 차이 확인 및 중간값 계산
    updated_results = []
    i = 0
    while i < len(result_df) - 1:
        current_row = result_df.iloc[i]
        next_row = result_df.iloc[i + 1]
        
        # timestamp2와 다음 timestamp1의 차이 계산
        time_gap = next_row['timestamp1'] - current_row['timestamp2']
        
        if time_gap.total_seconds() >= 900:  # 15분 이상
            i += 1  # 다음 행으로 이동
        else:
            # running_time이 45분보다 큰지 확인
            if current_row['running_time'] > 45 and next_row['running_time'] > 45:
                # 중간값 계산
                mid_time = current_row['timestamp2'] + (next_row['timestamp1'] - current_row['timestamp2']) / 2
                new_timestamp2 = mid_time - pd.Timedelta(minutes=15)
                new_timestamp1 = mid_time + pd.Timedelta(minutes=15)

                # 새로운 running_time 계산
                new_running_time1 = (new_timestamp2 - current_row['timestamp1']).total_seconds() / 60
                new_running_time2 = (next_row['timestamp2'] - new_timestamp1).total_seconds() / 60
                
                # 기존 행 업데이트
                result_df.at[i, 'timestamp2'] = new_timestamp2
                result_df.at[i, 'running_time'] = new_running_time1
                
                # 다음 행의 timestamp1과 running_time 업데이트
                result_df.at[i + 1, 'timestamp1'] = new_timestamp1
                result_df.at[i + 1, 'running_time'] = new_running_time2

                i += 1
            else:    
                i += 1


    # 최종 결과 데이터프레임으로 변환
    final_df = result_df.copy()

    final_df.to_csv('schedule.csv', index=False)

    # 결과 출력
    print(final_df)
