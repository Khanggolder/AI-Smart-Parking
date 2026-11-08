FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/ai-service
RUN pip install --no-cache-dir torch==2.11.0+cpu torchvision==0.26.0+cpu --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir numpy==2.4.6 opencv-python-headless==5.0.0.93 Pillow==13.0.0 PyYAML==6.0.3 fastapi==0.162.0 uvicorn==0.54.0 python-multipart==0.0.32
COPY ai-service/src ./src
COPY ai-service/configs ./configs
EXPOSE 8001
CMD ["uvicorn", "src.service:app", "--host", "0.0.0.0", "--port", "8001"]
