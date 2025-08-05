import re
import os
import tempfile
import pandas as pd
import streamlit as st
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import plotly.express as px
import plotly.io as pio
import json
import time
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
import base64
import xlsxwriter

# ----------------------- YOUR CSS (Keep exactly as is) --------------------------
def load_css(theme):
    if theme == "Dark Mode":
        pio.templates.default = "plotly_dark"
        st.markdown("""<style>
            .stApp { background-color: #0e1117; color: #f8f9fa; }
            h1 { color: #f8f9fa; text-align: center; font-weight: 900; margin-bottom: 25px; }
            h2,h3,h4,h5,h6,p,div,span { color: #f8f9fa !important; }
            textarea, input {
                background-color: #1e1e1e !important;
                color: #ffffff !important;
                border: 2px solid #4cafef !important;
                border-radius: 8px !important;
            }
            div.stButton > button {
                background: linear-gradient(90deg, #00c6ff, #0072ff);
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 0.5em 1.2em;
                transition: all 0.3s ease-in-out;
            }
            div.stButton > button:hover {
                transform: scale(1.05);
                background: linear-gradient(90deg, #0072ff, #00c6ff);
            }
            .stDownloadButton button {
                background: linear-gradient(90deg, #f39c12, #e67e22);
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 0.5em 1.2em;
            }
            .card-container {
                display: flex;
                justify-content: space-evenly;
                flex-wrap: wrap;
                gap: 25px;
                margin-top: 25px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #1e1e1e;
                border-radius: 14px;
                padding: 20px 25px;
                width: 22%;
                min-width: 220px;
                text-align: center;
                color: #f8f9fa;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                transition: all 0.3s ease-in-out;
            }
            .stat-card:hover {
                transform: translateY(-5px) scale(1.03);
                box-shadow: 0 8px 20px rgba(0, 255, 176, 0.6);
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                margin-bottom: 8px;
                color: #00ffb0;
            }
            .stat-label {
                font-size: 1.05em;
                font-weight: 500;
            }
            .loader {
                border: 6px solid #f3f3f3;
                border-top: 6px solid #00ffb0;
                border-radius: 50%;
                width: 55px;
                height: 55px;
                animation: spin 1s linear infinite;
                margin: 25px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            </style>""", unsafe_allow_html=True)
    else:
        pio.templates.default = "plotly_white"
        st.markdown("""<style>
            .stApp { background-color: #f7f9fc; color: #2c3e50; }
            h1 { color: #2c3e50; text-align: center; font-weight: 900; margin-bottom: 25px; }
            textarea, input {
                border-radius: 8px !important;
                border: 2px solid #2ecc71 !important;
                background-color: #ffffff !important;
                color: #2c3e50 !important;
            }
            div.stButton > button {
                background: linear-gradient(90deg, #3498db, #2ecc71);
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 0.5em 1.2em;
                transition: all 0.3s ease-in-out;
            }
            div.stButton > button:hover {
                transform: scale(1.05);
                background: linear-gradient(90deg, #2ecc71, #3498db);
            }
            .stDownloadButton button {
                background: linear-gradient(90deg, #e67e22, #f39c12);
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 0.5em 1.2em;
            }
            .card-container {
                display: flex;
                justify-content: space-evenly;
                flex-wrap: wrap;
                gap: 25px;
                margin-top: 25px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #ffffff;
                border-radius: 14px;
                padding: 20px 25px;
                width: 22%;
                min-width: 220px;
                text-align: center;
                color: #2c3e50;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                transition: all 0.3s ease-in-out;
            }
            .stat-card:hover {
                transform: translateY(-5px) scale(1.03);
                box-shadow: 0 8px 20px rgba(52, 152, 219, 0.5);
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                margin-bottom: 8px;
                color: #2ecc71;
            }
            .stat-label {
                font-size: 1.05em;
                font-weight: 500;
            }
            .loader {
                border: 6px solid #f3f3f3;
                border-top: 6px solid #3498db;
                border-radius: 50%;
                width: 55px;
                height: 55px;
                animation: spin 1s linear infinite;
                margin: 25px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            </style>""", unsafe_allow_html=True)
# -------------------------------------------------------------------------------

# --------------------- Helper Functions ----------------------

def parse_http_error(err: HttpError):
    try:
        error_content = json.loads(err.content.decode("utf-8"))
        return "❌ Error: " + error_content["error"]["message"]
    except:
        return "❌ Error: Unknown API error occurred."

def human_format(num):
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)

def get_channel_id(youtube, url):
    # Try /channel/ID
    match = re.search(r'/channel/([A-Za-z0-9_-]+)', url)
    if match:
        return match.group(1)
    # Try /@username
    match = re.search(r'/@([A-Za-z0-9_-]+)', url)
    if match:
        username = match.group(1)
        req = youtube.search().list(part='snippet', q=username, type='channel', maxResults=1)
        res = req.execute()
        return res['items'][0]['snippet']['channelId']
    # Try from video URL
    query = urlparse(url).query
    video_id = parse_qs(query).get('v')
    if video_id:
        vid = video_id[0]
        req = youtube.videos().list(part='snippet', id=vid)
        res = req.execute()
        return res['items'][0]['snippet']['channelId']
    raise ValueError("❌ Could not detect channel ID from URL.")

def get_channel_stats(youtube, channel_id):
    req = youtube.channels().list(part="snippet,statistics,contentDetails", id=channel_id)
    res = req.execute()
    data = res['items'][0]
    stats = data['statistics']
    snippet = data['snippet']
    playlist_id = data['contentDetails']['relatedPlaylists']['uploads']
    return {
        "title": snippet['title'],
        "subscribers": int(stats.get('subscriberCount', 0)),
        "totalViews": int(stats.get('viewCount', 0)),
        "totalVideos": int(stats.get('videoCount', 0)),
        "publishedAt": snippet['publishedAt'],
        "uploadsPlaylist": playlist_id
    }

def get_all_video_ids(youtube, playlist_id, max_results=50):
    video_ids = []
    next_page_token = None
    while True:
        req = youtube.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=next_page_token)
        res = req.execute()
        for item in res['items']:
            video_ids.append(item['contentDetails']['videoId'])
        next_page_token = res.get('nextPageToken')
        if not next_page_token or len(video_ids) >= max_results:
            break
    return video_ids[:max_results]

def get_video_details(youtube, video_ids):
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        req = youtube.videos().list(part="snippet,statistics", id=",".join(batch))
        res = req.execute()
        for item in res['items']:
            snippet = item['snippet']
            stats = item['statistics']
            video_id = item['id']
            tags = snippet.get('tags', [])
            videos.append({
                "title": snippet['title'],
                "views": int(stats.get('viewCount', 0)),
                "likes": int(stats.get('likeCount', 0)),
                "comments": int(stats.get('commentCount', 0)),
                "publishedAt": snippet['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": snippet['thumbnails']['medium']['url'],
                "tags": tags,
                "description": snippet.get('description', '')
            })
    return videos

def extract_keywords_from_channel(videos):
    # Combine all titles, tags, descriptions
    text = " ".join(v['title'] for v in videos) + " "
    text += " ".join(" ".join(v['tags']) for v in videos if v['tags']) + " "
    text += " ".join(v['description'] for v in videos)
    # Simple cleanup and split
    words = re.findall(r'\b\w{3,}\b', text.lower())
    counter = Counter(words)
    return dict(counter.most_common(100))  # top 100 keywords

def generate_wordcloud(keywords):
    wc = WordCloud(width=400, height=200, background_color="white").generate_from_frequencies(keywords)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf

def simulate_ranking_for_videos(youtube, keywords, videos):
    # Simulate video ranking by checking keyword occurrence in title/tags
    ranking = []
    for video in videos:
        video_keywords = set()
        # Combine title+tags
        combined_text = (video['title'] + " " + " ".join(video['tags'])).lower()
        for kw in keywords:
            if kw.lower() in combined_text:
                video_keywords.add(kw)
        if video_keywords:
            ranking.append({
                "video_title": video['title'],
                "video_url": video['url'],
                "views": video['views'],
                "matched_keywords": list(video_keywords),
                "thumbnail": video['thumbnail']
            })
    # Sort by views desc
    ranking.sort(key=lambda x: x['views'], reverse=True)
    return ranking[:2]  # top 2 videos only

def generate_pdf_report(channels_data, ranking_data):
    def safe_str(s):
        if not isinstance(s, str):
            s = str(s)
        return s.encode('latin-1', 'replace').decode('latin-1')

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)

    for ch_data in channels_data:
        ch_stats = ch_data['stats']
        ch_title = ch_stats['title']
        pdf.add_page()
        pdf.cell(0, 10, safe_str(f"Channel: {ch_title}"), ln=True, align='C')

        pdf.set_font("Arial", size=12)
        pdf.ln(5)
        pdf.cell(0, 8, safe_str(f"Subscribers: {human_format(ch_stats['subscribers'])}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Total Views: {human_format(ch_stats['totalViews'])}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Total Videos: {human_format(ch_stats['totalVideos'])}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Engagement Rate: {ch_data['engagement_rate']:.2f}%"), ln=True)
        pdf.cell(0, 8, safe_str(f"Est. Monthly Revenue: ${ch_data['monthly_min']:.2f} - ${ch_data['monthly_max']:.2f}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Est. Yearly Revenue: ${ch_data['yearly_min']:.2f} - ${ch_data['yearly_max']:.2f}"), ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, safe_str("Top 2 Ranked Videos:"), ln=True)
        pdf.set_font("Arial", size=12)
        for vid in ranking_data.get(ch_title, []):
            # Thumbnail image
            try:
                import requests
                response = requests.get(vid['thumbnail'])
                if response.status_code == 200:
                    import tempfile, os
                    img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    pdf.image(img_path, w=40, h=30)
                    os.remove(img_path)
                else:
                    pdf.cell(0, 10, safe_str("Thumbnail not available."), ln=True)
            except Exception:
                pdf.cell(0, 10, safe_str("Thumbnail not available."), ln=True)

            pdf.cell(0, 10, safe_str(f"Title: {vid['video_title']}"), ln=True)
            pdf.set_text_color(0, 0, 255)
            pdf.cell(0, 10, safe_str(f"Link: {vid['video_url']}"), ln=True, link=vid['video_url'])
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, safe_str(f"Views: {human_format(vid['views'])}"), ln=True)
            pdf.cell(0, 10, safe_str(f"Matched Keywords: {', '.join(vid['matched_keywords'])}"), ln=True)
            pdf.ln(5)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, safe_str("Top Keywords:"), ln=True)
        pdf.set_font("Arial", size=12)

        keywords = ch_data.get("keywords", {})
        top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]
        for k, v in top_keywords:
            pdf.cell(0, 10, safe_str(f"{k}: {v}"), ln=True)

    import tempfile
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_file.name)
    return tmp_file.name

def create_excel_download(data_records):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df = pd.DataFrame(data_records)
        df.to_excel(writer, index=False, sheet_name="YouTube Analysis")
    processed_data = output.getvalue()
    return processed_data

# ---------------------- Streamlit UI --------------------------



st.set_page_config(page_title="YouTube Channel Analyzer", layout="wide")

if "channels_data" not in st.session_state:
    st.session_state["channels_data"] = []
if "csv_records" not in st.session_state:
    st.session_state["csv_records"] = []
if "analysis_done" not in st.session_state:
    st.session_state["analysis_done"] = False
if "ranking_data" not in st.session_state:
    st.session_state["ranking_data"] = {}
if "channel_keywords" not in st.session_state:
    st.session_state["channel_keywords"] = {}
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""
if "theme" not in st.session_state:
    st.session_state["theme"] = "Light Mode"

theme = st.sidebar.radio("🎨 Theme", ["Light Mode", "Dark Mode"],
                         index=0 if st.session_state["theme"] == "Light Mode" else 1)
st.session_state["theme"] = theme
load_css(theme)

import streamlit as st
from streamlit_oauth import OAuth2Component
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from collections import Counter
import pandas as pd
import base64, os, tempfile
from fpdf import FPDF
import jwt
import requests

# ✅ Your 4 API Keys
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from collections import Counter
import pandas as pd
import base64, os, tempfile
from fpdf import FPDF

# ✅ Your 4 API Keys
API_KEYS = [
    "AIzaSyDIHJHs9-bCTQuDDQiX7nxujYvjlanolYY",
    "AIzaSyBzwWrSAE4AdqGeOpz--f7n5zU6bBdzBX0",
    "AIzaSyAzUf0lQOg-8tW7A4xqnv1pz4RZ5ljapp8",
    "AIzaSyBFZ12HeFKwMoOPnnBvltyQqda27nnLVas"
]

# ✅ API Key Rotation Logic
current_key_index = 0

def get_youtube_client():
    global current_key_index
    for i in range(len(API_KEYS)):
        key_to_use = API_KEYS[current_key_index]
        try:
            yt = build('youtube', 'v3', developerKey=key_to_use)
            # Test call to verify key
            yt.channels().list(part='id', id='UC_x5XG1OV2P6uZZ5FSM9Ttw').execute()
            st.session_state["api_key"] = key_to_use
            return yt
        except HttpError as e:
            error_message = str(e)
            if "quotaExceeded" in error_message or "invalid" in error_message:
                current_key_index = (current_key_index + 1) % len(API_KEYS)
            else:
                raise e
    st.error("❌ All API keys exhausted or invalid.")
    st.stop()

# ✅ Utility function to fix Unicode for PDF
def safe_str(s):
    if not isinstance(s, str):
        s = str(s)
    return s.encode('latin-1', 'replace').decode('latin-1')

# ✅ PDF Report Function with Unicode Fix
def generate_pdf_report(channels_data, ranking_data):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)

    for ch_data in channels_data:
        ch_stats = ch_data['stats']
        ch_title = ch_stats['title']
        pdf.add_page()
        pdf.cell(0, 10, safe_str(f"Channel: {ch_title}"), ln=True, align='C')

        pdf.set_font("Arial", size=12)
        pdf.ln(5)
        pdf.cell(0, 8, safe_str(f"Subscribers: {human_format(ch_stats['subscribers'])}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Total Views: {human_format(ch_stats['totalViews'])}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Total Videos: {human_format(ch_stats['totalVideos'])}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Engagement Rate: {ch_data['engagement_rate']:.2f}%"), ln=True)
        pdf.cell(0, 8, safe_str(f"Est. Monthly Revenue: ${ch_data['monthly_min']:.2f} - ${ch_data['monthly_max']:.2f}"), ln=True)
        pdf.cell(0, 8, safe_str(f"Est. Yearly Revenue: ${ch_data['yearly_min']:.2f} - ${ch_data['yearly_max']:.2f}"), ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, safe_str("Top 2 Ranked Videos:"), ln=True)
        pdf.set_font("Arial", size=12)
        for vid in ranking_data.get(ch_title, []):
            try:
                import requests
                response = requests.get(vid['thumbnail'])
                if response.status_code == 200:
                    img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    pdf.image(img_path, w=40, h=30)
                    os.remove(img_path)
            except:
                pdf.cell(0, 10, safe_str("Thumbnail not available."), ln=True)

            pdf.cell(0, 10, safe_str(f"Title: {vid['video_title']}"), ln=True)
            pdf.set_text_color(0, 0, 255)
            pdf.cell(0, 10, safe_str(f"Link: {vid['video_url']}"), ln=True, link=vid['video_url'])
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, safe_str(f"Views: {human_format(vid['views'])}"), ln=True)
            pdf.cell(0, 10, safe_str(f"Matched Keywords: {', '.join(vid['matched_keywords'])}"), ln=True)
            pdf.ln(5)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, safe_str("Top Keywords:"), ln=True)
        pdf.set_font("Arial", size=12)

        keywords = ch_data.get("keywords", {})
        top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]
        for k, v in top_keywords:
            pdf.cell(0, 10, safe_str(f"{k}: {v}"), ln=True)

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_file.name)
    return tmp_file.name

# ✅ Your Original Streamlit Code with Key Rotation Integrated
st.title("📊 YouTube Channel Analyzer + Competitor + Revenue + Ranking")


with st.form("channels_form"):
    st.markdown("### 🔗 Enter YouTube Channel URLs (one per line)")
    urls = st.text_area("Channel URLs", height=150)
    submitted = st.form_submit_button("Analyze Channels")

if submitted:
    youtube = get_youtube_client()

    channel_urls = list(set([u.strip() for u in urls.strip().split('\n') if u.strip()]))
    channels_data = []
    csv_records = []

    with st.spinner("⏳ Fetching channel data..."):
        for url in channel_urls:
            try:
                channel_id = get_channel_id(youtube, url)
                stats = get_channel_stats(youtube, channel_id)
                video_ids = get_all_video_ids(youtube, stats["uploadsPlaylist"], max_results=50)
                videos = get_video_details(youtube, video_ids)
                total_views = sum(v['views'] for v in videos) or 1
                total_likes = sum(v['likes'] for v in videos)
                total_comments = sum(v['comments'] for v in videos)
                engagement_rate = 100 * (total_likes + total_comments) / total_views

                monthly_min = (stats["totalViews"] / 1000) * 1
                monthly_max = (stats["totalViews"] / 1000) * 3
                yearly_min = monthly_min * 12
                yearly_max = monthly_max * 12

                keywords = extract_keywords_from_channel(videos)

                channels_data.append({
                    "url": url,
                    "id": channel_id,
                    "stats": stats,
                    "videos": videos,
                    "engagement_rate": engagement_rate,
                    "monthly_min": monthly_min,
                    "monthly_max": monthly_max,
                    "yearly_min": yearly_min,
                    "yearly_max": yearly_max,
                    "keywords": keywords
                })

                for vid in videos:
                    csv_records.append({
                        "Channel": stats['title'],
                        "Video Title": vid['title'],
                        "Views": vid['views'],
                        "Likes": vid['likes'],
                        "Comments": vid['comments'],
                        "Published At": vid['publishedAt'],
                        "URL": vid['url']
                    })
            except HttpError as e:
                st.error(parse_http_error(e))
            except Exception as e:
                st.error(f"Error processing URL {url}: {e}")

    st.session_state["channels_data"] = channels_data
    st.session_state["csv_records"] = csv_records
    st.session_state["analysis_done"] = True
    st.session_state["channel_keywords"] = {ch['stats']['title']: ch['keywords'] for ch in channels_data}

if st.session_state.get("analysis_done"):
    youtube = get_youtube_client()

    st.markdown("---")
    st.header("📈 Channel Summary Cards")
    cols = st.columns(len(st.session_state["channels_data"]))
    for idx, ch in enumerate(st.session_state["channels_data"]):
        stats = ch['stats']
        with cols[idx]:
            st.markdown(f"### {stats['title']}")
            st.markdown(f"**Subscribers:** {human_format(stats['subscribers'])}")
            st.markdown(f"**Total Views:** {human_format(stats['totalViews'])}")
            st.markdown(f"**Total Videos:** {human_format(stats['totalVideos'])}")
            st.markdown(f"**Engagement Rate:** {ch['engagement_rate']:.2f}%")
            st.markdown(f"**Monthly Revenue:** ${ch['monthly_min']:.2f} - ${ch['monthly_max']:.2f}")

    # Ranking
    st.markdown("---")
    st.header("🔍 Video Ranking Simulation (Top 2 Videos per Channel)")
    ranking_data = {}
    for ch in st.session_state["channels_data"]:
        ch_title = ch['stats']['title']
        keywords = list(st.session_state["channel_keywords"][ch_title].keys())
        ranking = simulate_ranking_for_videos(youtube, keywords, ch['videos'])
        ranking_data[ch_title] = ranking
    st.session_state["ranking_data"] = ranking_data

    for ch_title, vids in ranking_data.items():
        st.subheader(f"Top Ranked Videos for {ch_title}")
        for vid in vids:
            st.markdown(f"**[{vid['video_title']}]({vid['video_url']})**")
            st.image(vid['thumbnail'], width=320)
            st.markdown(f"Views: {human_format(vid['views'])}")
            st.markdown(f"Matched Keywords: {', '.join(vid['matched_keywords'])}")
            st.markdown("---")

    # Keyword Analysis
    st.markdown("---")
    st.header("📊 Keyword Frequency & Word Clouds Per Channel")
    for ch in st.session_state["channels_data"]:
        ch_title = ch['stats']['title']
        keywords = ch['keywords']
        st.subheader(f"{ch_title} Keywords")
        if keywords:
            freq_df = pd.DataFrame(list(keywords.items()), columns=["Keyword", "Frequency"]).sort_values(by="Frequency", ascending=False)
            st.dataframe(freq_df.head(20))
            wc_img = generate_wordcloud(keywords)
            st.image(wc_img)

    # Global Keywords
    st.markdown("---")
    st.header("🌍 Global Keyword Analysis")
    combined_keywords = Counter()
    for ch in st.session_state["channels_data"]:
        combined_keywords.update(ch['keywords'])
    combined_keywords = dict(combined_keywords.most_common(50))
    global_df = pd.DataFrame(list(combined_keywords.items()), columns=["Keyword", "Frequency"])

    channel_filter = st.selectbox("Filter keywords by Channel (or select All)", ["All"] + [ch['stats']['title'] for ch in st.session_state["channels_data"]])
    if channel_filter != "All":
        kwds = st.session_state["channel_keywords"].get(channel_filter, {})
        filtered_df = pd.DataFrame(list(kwds.items()), columns=["Keyword", "Frequency"]).sort_values(by="Frequency", ascending=False)
        st.dataframe(filtered_df.head(50))
        wc_img = generate_wordcloud(kwds)
        st.image(wc_img)
        st.markdown(f"### Top Ranked Videos for {channel_filter}")
        for vid in st.session_state["ranking_data"].get(channel_filter, []):
            st.markdown(f"**[{vid['video_title']}]({vid['video_url']})**")
            st.image(vid['thumbnail'], width=250)
            st.markdown(f"Views: {human_format(vid['views'])}")
            st.markdown(f"Matched Keywords: {', '.join(vid['matched_keywords'])}")
            st.markdown("---")
    else:
        st.dataframe(global_df)
        wc_img = generate_wordcloud(combined_keywords)
        st.image(wc_img)

    # Downloads
    st.markdown("---")
    st.header("💾 Download Reports")

    csv_df = pd.DataFrame(st.session_state["csv_records"])
    csv = csv_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, file_name="youtube_analysis.csv", mime="text/csv")

    excel_bytes = create_excel_download(st.session_state["csv_records"])
    st.download_button("Download Excel", excel_bytes, file_name="youtube_analysis.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    pdf_path = generate_pdf_report(st.session_state["channels_data"], st.session_state["ranking_data"])
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="youtube_report.pdf">Download PDF Report</a>'
    st.markdown(href, unsafe_allow_html=True)
    os.remove(pdf_path)


