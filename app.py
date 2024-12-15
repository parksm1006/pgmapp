import streamlit as st
from xml.dom.minidom import parseString
import pandas as pd
import urllib.request
from collections import Counter
import os
import time
from konlpy.tag import Okt
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib as mpl

font_path = 'malgun.ttf'
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)
plt.rcParams['axes.unicode_minus'] =False

#소개글
st.title(':green[네이버] :blue[뉴스 트렌드 분석기]에 온것을 환영합니다~!')
st.divider()
st.subheader(':green[네이버] :blue[뉴스 트렌드 분석기]란?')
mt_1='''
:blue[원하는 키워드]에 대한 뉴스를 총 :red[1000]개 검색 후 기사 제목에서 단어를 분해해서 빈도수 분석을 하는 :orange[웹 애플리케이션]입니다.

그럼 시작해 볼까요?
'''
st.markdown(mt_1)
st.divider()

client_id=st.secrets['api_keys']['client_id']
client_secret=st.secrets['api_keys']['client_secret']

if "form_submitted" not in st.session_state:
    st.session_state['form_submitted']='False'
if "df" not in st.session_state:
    st.session_state['df']=None

data_list = []

#검색 단어 폼
with st.form('searching_text'):
    key_word={'query':st.text_input('원하는 키워드를 하나 적으세요',placeholder='ex)과학기술, 파이썬 등')}
    submit_button = st.form_submit_button('단어 입력')

    if submit_button:
        encoded_key_word=urllib.parse.urlencode(key_word)

        def fetch_data(url):
            request = urllib.request.Request(url)
            request.add_header('X-Naver-Client-ID', client_id)
            request.add_header('X-Naver-Client-Secret', client_secret)
            response = urllib.request.urlopen(request)
            rescode = response.getcode()
            
            if rescode == 200:
                response_body = response.read()
                return response_body.decode('utf-8')
            else:
                print(f"API 호출 실패: {rescode}")
                return None

        # 10번 API 호출하여 데이터 수집
        for i in range(10):
            time.sleep(0.1)
            start = i * 100 + 1
            url = f'https://openapi.naver.com/v1/search/news.xml?{encoded_key_word}&display=100&start={start}&sort=date'
            raw_data = fetch_data(url)
            
            if raw_data:
                dom = parseString(raw_data)
                for item in dom.getElementsByTagName('item'):
                    title = item.getElementsByTagName('title')[0].firstChild.nodeValue
                    link = item.getElementsByTagName('link')[0].firstChild.nodeValue
                    pubDate = item.getElementsByTagName('pubDate')[0].firstChild.nodeValue
                    
                    data = {
                        'Title': title,
                        'Link': link,
                        'Time': pubDate
                    }
                    data_list.append(data)

        df = pd.DataFrame(data_list)
        path=os.path.abspath("news_title.xlsx")
        df.to_excel(path, index=False)
        # 한국어 불용어 목록을 파일에서 읽어오기
        with open('stopwords-ko.txt', 'r', encoding='utf-8') as f:
            korean_stopwords = set(f.read().splitlines())
        
        def preprocess_korean(text):
            text = re.sub(r'[^\w\s]', '', text)
            okt = Okt()
            tokens = okt.morphs(text, stem=True)
            filtered_tokens = [token for token in tokens if token not in korean_stopwords and token.isalnum()]
            return ' '.join(filtered_tokens)
        
        input_filename = 'news_title.xlsx'
        df = pd.read_excel(input_filename)

        df['Processed_title'] = df['Title'].apply(preprocess_korean)

        st.session_state['df']=df

        output_filename = 'processed_news_title.xlsx'
        df.to_excel(output_filename, index=False)

        all_words = [word for title in df['Processed_title'] for word in title.split()]

        word_counts = Counter(all_words)

        word_df = pd.DataFrame(word_counts.items(), columns=['Word', 'Count'])
        word_df = word_df.sort_values(by='Count', ascending=False)

        word_df.to_excel('word_count.xlsx', index=False)

        st.session_state['form_submitted']=True


if st.session_state['form_submitted'] and st.session_state['df'] is not None:
    with open('processed_news_title.xlsx','rb') as file:
        file_data=file.read()
    st.download_button(
                       label='시간별 네이버 기사 제목 데이터',
                       data=file_data,
                       file_name='형태소 분석 결과.xlsx',
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
if st.session_state['form_submitted']:
    with st.form('visualization'):
        options=st.multiselect(
            "시각화 할 방법을 선택하세요",
            ["워드클라우드","단어 총 갯수 top10","날짜별 단어 빈도","시간별 단어 빈도"],
            ["워드클라우드"]
        )
        submit_button = st.form_submit_button('시각화')
        word_df = pd.read_excel('word_count.xlsx')
        top_words = word_df[word_df['Count'] >= 5].nlargest(5, 'Count')['Word'].tolist()
        if submit_button and "워드클라우드" in options:
            

            filtered_words = word_df[word_df['Count'] >= 5]

            word_freq = dict(zip(filtered_words['Word'], filtered_words['Count']))

            wordcloud = WordCloud(
                font_path='malgun.ttf',  # 한글 폰트 경로
                background_color='white',
                width=800,
                height=600
            ).generate_from_frequencies(word_freq)

            plt.figure(figsize=(12, 8))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.title('워드 클라우드')
            st.pyplot(plt)

        if submit_button and "단어 총 갯수 top10" in options:
            top_10_words=word_df.nlargest(10,'Count')

            plt.figure(figsize=(10,6))
            plt.bar(top_10_words['Word'],top_10_words['Count'],color='orange')
            plt.xlabel('단어')
            plt.ylabel('총 갯수')
            plt.title("단어 총 갯수 top10")
            plt.xticks(rotation=45)
            st.pyplot(plt)


        if submit_button and "날짜별 단어 빈도" in options:
            df = pd.read_excel('processed_news_title.xlsx')

            df['Date'] = pd.to_datetime(df['Time']).dt.date
            date_word_counts = {}
            for date, title in zip(df['Date'], df['Processed_title']):
                words = title.split()
                relevant_words = [word for word in words if word in top_words]
                if date not in date_word_counts:
                    date_word_counts[date] = Counter()
                date_word_counts[date].update(relevant_words)

            output_data = []
            for date, counter in date_word_counts.items():
                for word, count in counter.items():
                    output_data.append({'Date': date, 'Word': word, 'Frequency': count})

            data_df = pd.DataFrame(output_data)

            plt.figure(figsize=(14, 8))
            for word in data_df['Word'].unique():
                word_data = data_df[data_df['Word'] == word]
                plt.plot(word_data['Date'], word_data['Frequency'], label=word)

            plt.xlabel('날짜')
            plt.ylabel('빈도')
            plt.title('날짜별 단어 빈도')
            plt.legend()
            plt.grid(True)
            st.pyplot(plt)


        if submit_button and "시간별 단어 빈도" in options:
            df = pd.read_excel('processed_news_title.xlsx')
            df['Date'] = pd.to_datetime(df['Time']).dt.date

            most_common_date = df['Date'].value_counts().idxmax()
            
            filtered_df = df[df['Date'] == most_common_date].copy()

            filtered_df['Time_h'] = pd.to_datetime(filtered_df['Time']).dt.hour

            hour_word_counts = {}
            for hour, title in zip(filtered_df['Time_h'], filtered_df['Processed_title']):
                words = title.split()
                relevant_words = [word for word in words if word in top_words]
                if hour not in hour_word_counts:
                    hour_word_counts[hour] = Counter()
                hour_word_counts[hour].update(relevant_words)

            output_data = []
            for hour, counter in hour_word_counts.items():
                for word, count in counter.items():
                    output_data.append({'Time_h': hour, 'Word': word, 'Frequency': count})

            data_df = pd.DataFrame(output_data)
            plt.figure(figsize=(14, 8))
            for word in data_df['Word'].unique():
                word_data = data_df[data_df['Word'] == word]
                plt.plot(word_data['Time_h'], word_data['Frequency'], label=word)

            plt.xlabel('시간')
            plt.ylabel('빈도')
            plt.title('시간별 단어 빈도')
            plt.legend()
            plt.grid(True)
            st.pyplot(plt)
            st.caption("시간별 단어 빈도는 기사가 가장 많이 올라온 날을 기준으로 하고 있습니다.")
