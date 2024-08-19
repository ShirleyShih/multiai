# 使用 Python 的基礎映像
FROM python:3.9

# 設置工作目錄
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# 安裝依賴
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# 暴露應用埠
EXPOSE 80

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
