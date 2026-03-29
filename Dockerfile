FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install streamlit requests folium streamlit-folium

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]