# uvicorn app:app --reload
# pip install openai
# pip install google-generativeai
# pip install genai
# pip install anthropic
# pip install python-dotenv
# pip install google-cloud-speech
from fastapi import *
from fastapi import FastAPI, Request, Response, Depends, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv
import os

import openai
# from openai.error import RateLimitError

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# from genai.exceptions import GenAIError, RateLimitError, AuthenticationError

import anthropic

import mysql.connector
from mysql.connector import Error
from data.dbconfig import db_config

from pydantic import BaseModel
from typing import Optional

import jwt
from fastapi.security import OAuth2PasswordBearer
import datetime
import boto3
import uuid

import imghdr
from PIL import Image
import io
import base64
import httpx

app=FastAPI()

app.mount("/static", StaticFiles(directory="static"))

# templates = Jinja2Templates(directory="templates")

@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")
@app.get("/conversation/{conversation_id}", include_in_schema=False)
async def conversation(request: Request, conversation_id: str):
	return FileResponse("./static/index.html", media_type="text/html")

load_dotenv()

################## member system
SECRET_KEY="abc"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expiration time

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    name: str
    email: str
    password: str

@app.post("/api/user")
async def signup(response: Response, user: User):
    try:
        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()
        cursor.execute("select * from member where email=%s",(user.email,))
        result=cursor.fetchone()

        if result:
            response.status_code=400
            return {"error": True, "message": "此電子信箱已註冊"}
        
        cursor.execute("insert into member(name,email,password) values(%s,%s,%s)",(user.name,user.email,user.password))
        con.commit()

        response.status_code=200
        return {"ok": True, "message": "註冊成功"}
    
    except Error as e:
        response.status_code=500
        return {"error": True, "message": "內部伺服器錯誤"}

    finally:
        cursor.close()
        con.close()

class User_signin(BaseModel):
    email: str
    password: str

def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
    
@app.put("/api/user/auth")
async def login(response: Response, user: User_signin):
    con = None
    cursor = None
    try:
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        cursor.execute("SELECT id, name FROM member WHERE email=%s AND password=%s", (user.email, user.password))
        result = cursor.fetchone()

        if not result:
            response.status_code = 400
            return {"error": True, "message": "電子信箱或密碼錯誤"}
        
        user_id, name = result
        token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(data={"id": user_id, "name": name, "email": user.email}, expires_delta=token_expires)
        # print(token)
        return {"token": token, "message": "登入成功"}
    
    except Error as e:
        response.status_code = 500
        return {"error": True, "message": "內部伺服器錯誤"}
    
    finally:
        if cursor:
            cursor.close()
        if con:
            con.close()

# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=401,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("id")
#         # if user_id is None:
#         #     raise credentials_exception
#     except jwt.PyJWTError:
#         raise credentials_exception
#     return payload

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        if user_id is None:
            return None  # Return None if user_id is not found
        return payload
    except jwt.PyJWTError:
        return None  # Return None if token verification fails

@app.get("/api/user/auth")
async def get_user(current_user: dict = Depends(get_current_user)):
    print(current_user)
    return {"data": current_user}

######################### Conversation history
def current_memberid(current_user):
    if current_user is None:
        memberid=0
    else:
        memberid=current_user["id"]
    return memberid

# class Request(BaseModel):
#     request_text: str
#     request_id: str
#     image: Optional[UploadFile] = None

# class Request(BaseModel):
#     request_text: str = Form(...)
#     request_id: str = Form(...)
#     image: Optional[UploadFile] = None

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION')
)

# Define S3 bucket
S3_BUCKET = os.environ.get('AWS_BUCKET_NAME')
import pytz
@app.post("/api/conversation/{conversation_id}")
async def create_conversation(response: Response,
                              conversation_id: str,
                              request_text: str = Form(...),
                              request_id: str = Form(...),
                              timeZone: str = Form(...),
                              image: Optional[UploadFile] = File(None),
                              current_user: dict = Depends(get_current_user)):
    try:
        # print(current_user)
        memberid=current_memberid(current_user)
        # print(memberid)

        # Get the current UTC time
        utc_now = datetime.datetime.now(pytz.utc)

        # Convert to user's time zone
        user_time_zone = pytz.timezone(timeZone)
        user_time = utc_now.astimezone(user_time_zone)

        current_date = user_time.strftime("%Y-%m-%d")
        current_time = user_time.strftime("%H:%M:%S")
        # print(user_time,current_date,current_time)

        # current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        # current_time = datetime.datetime.now().strftime("%H:%M:%S")
    
        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()
        cursor.execute("""select title from conversation
                    where conversation_id=%s and memberid=%s""",
                    (conversation_id,memberid))
        title = cursor.fetchone()
        # print(title)

        if not title:
            title=f"Conversation at {current_date} {current_time}"
            # print(current_date, current_time)

            cursor.execute("""insert into conversation(memberid,conversation_id,title) 
                values(%s,%s,%s)""",
                (memberid,conversation_id,title))
            con.commit()
            # Retrieve the ID of the newly inserted record
            # conversation_id = cursor.lastrowid
        # print(title)

        # insert new request
        if title:
            # upload selected image to s3
            file_url = None
            if image:
                file_content = await image.read()

                # Determine the image type (e.g., 'jpeg', 'png')
                image_type = imghdr.what(None, h=file_content)

                # Map the image type to file extension and ContentType
                extension_map = {
                    'jpeg': 'jpg',
                    'png': 'png'
                }
                if image_type in extension_map:
                    file_extension = extension_map[image_type]
                    imageno = f"{str(uuid.uuid4())}.{file_extension}"
                    s3.put_object(
                        Body=file_content,
                        Bucket=S3_BUCKET,
                        Key=imageno,
                        ContentType=f"image/{image_type}"
                    )
                    # print("File uploaded to S3 successfully")

                    file_url = f"https://d3cutng1gh49pz.cloudfront.net/{imageno}"
                    # print(f"File URL: {file_url}")

            # print(conversation_id)
            cursor.execute("""insert into request(conversation_id,request_id,request_text,date,time,imageurl) 
                values(%s,%s,%s,%s,%s,%s)""",
                (conversation_id,request_id,request_text,current_date,current_time,file_url)) #(user.name,user.email,user.password)
            con.commit()

            return {"ok": True, "imageurl": file_url, "message": "成功新增對話"}
            # return {"ok": True, "message": "成功新增對話"}

    except mysql.connector.Error as e:
        response.status_code = 500
        print("Database Error:", e)
        return {"error": True, "message": "Database error occurred."}
    
    except Error as e:
        return {"error": True, "message": str(e)}

    finally:
        if cursor is not None:
            cursor.close()
        if con is not None:
            con.close()

@app.get("/api/conversation")
async def get_dialog(response: Response, current_user: dict = Depends(get_current_user)):
    try:
        if not current_user:
            response.status_code=403
            return {"error":True,"message":"未登入系統，拒絕存取"}

        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()
        cursor.execute("""select conversation_id, title from conversation 
                       where memberid=%s""",(current_user["id"],)) # memberid
        result = cursor.fetchall()
        cursor.close()
        con.close()

        if result:
            return {"data": result}
        else:
            return {"error": True, "message": "conversation not found"}
    
    except Error as e:
        return {"error": True, "message": str(e)}

#################### OPENAI
openai.api_key=os.environ.get('OPENAI_KEY')

@app.get("/api/openai/{conversation_id}")
async def get_dialog(conversation_id: str, response: Response, current_user: dict = Depends(get_current_user)):
    try:
        memberid=current_memberid(current_user)

        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()
        cursor.execute("""select a.request_text, b.response_text, a.imageurl
                       from request a
                       inner join response_openai b
                       on a.request_id=b.request_id and a.conversation_id=%s
                       inner join conversation c
                       on a.conversation_id=c.conversation_id and c.memberid=%s
                       order by a.id""",(conversation_id,memberid))
        result = cursor.fetchall()
        cursor.close()
        con.close()

        if result:
            return {"data": result}
        else:
            return {"error": True, "message": "dialog not found"}
    
    except Error as e:
        return {"error": True, "message": str(e)}

# https://www.ithome.com.tw/news/155929
# https://www.youtube.com/watch?v=_1ujhANv6a4
@app.post("/api/openai")
async def fetchopenai(response: Response, 
                      request_text: str = Form(...),
                      request_id: str = Form(...),
                      imageurl: Optional[str] = Form(None),
                      current_user: dict = Depends(get_current_user)):
    cursor = None
    con = None
    try:
        memberid=1
        input_content = [{"type":"text","text":request_text}]
        
        if imageurl:
            input_content.append({"type":"image_url","image_url":{"url":imageurl,},})
        
        res = openai.ChatCompletion.create(
            model="gpt-4o",  # gpt-3.5-turbo
            messages=[{"role": "user", "content": input_content}],
            max_tokens=1000
        )
        # print(res)
        # res_text=res.choices[0]["text"].strip()
        res_text=res.choices[0].message.content.strip()
        # print(res_text)
        # request_id=res.id

        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()
        
        if res_text:
            cursor.execute("""insert into response_openai(request_id,response_text) 
                           values(%s,%s)""",
                           (request_id,res_text))
            con.commit()
            response.status_code=200
            return {"ok": True, "message": "成功取得openai response"}
        
    except openai.error.RateLimitError as e:
        response.status_code = 429
        print("Rate Limit Error:", e)
        return {"error": True, "message": "Rate limit exceeded. Please try again later."}

    except openai.error.AuthenticationError as e:
        print("Authentication Error:", e)

    except mysql.connector.Error as e:
        response.status_code = 500
        print("Database Error:", e)
        return {"error": True, "message": "Database error occurred."}
    
    except Error as e:
        response.status_code=500
        return {"error": True, "message": str(e)}

    finally:
        if cursor is not None:
            cursor.close()
        if con is not None:
            con.close()

###################### GEMINI
genai.configure(api_key=os.environ["GEMINI_KEY"])
# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

@app.get("/api/gemini/{conversation_id}")
async def get_dialog(conversation_id: str, response: Response, current_user: dict = Depends(get_current_user)):
    try:
        memberid=current_memberid(current_user)

        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()
        cursor.execute("""select a.request_text, b.response_text, a.imageurl
                       from request a
                       inner join response_gemini b
                       on a.request_id=b.request_id and a.conversation_id=%s
                       inner join conversation c
                       on a.conversation_id=c.conversation_id and c.memberid=%s
                       order by a.id""",(conversation_id,memberid))
        result = cursor.fetchall()
        cursor.close()
        con.close()

        if result:
            return {"data": result}
        else:
            return {"error": True, "message": "dialog not found"}

    except Error as e:
        return {"error": True, "message": str(e)}

# https://medium.com/@m.alruqimi/image-analysis-using-gemini-pro-model-medical-images-analysis-as-a-case-study-9cda129a3176
@app.post("/api/gemini")
async def fetchgemini(response: Response, 
                      request_text: str = Form(...),
                      request_id: str = Form(...),
                      imageurl: Optional[UploadFile] = File(None),
                      current_user: dict = Depends(get_current_user)):
    cursor = None
    con = None
    try:
        memberid = 1
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            }
        )

        if imageurl:
            image_bytes = await imageurl.read()
            image = Image.open(io.BytesIO(image_bytes))
            response = model.generate_content([request_text,image])
        else:
            # Initialize the chat session
            chat_session = model.start_chat(history=[])
            response = chat_session.send_message(request_text) # stream=True 串流即時通訊

        # print(response)
        res_text=response.text
        # print(res_text)

        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()

        if res_text:
            cursor.execute("""insert into response_gemini(request_id,response_text) 
                           values(%s,%s)""",
                           (request_id,res_text))
            con.commit()
            response.status_code=200
            return {"ok": True, "message": "成功取得Gemini response"}
        
    except Exception as e:
        response.status_code = 500
        print("Unexpected Error:", e)
        return {"error": True, "message": "An unexpected error occurred."}

    finally:
        if cursor is not None:
            cursor.close()
        if con is not None:
            con.close()

###################### CLAUDE3
client = anthropic.Anthropic( api_key = os.environ["CLAUDE_KEY"])

@app.get("/api/claude/{conversation_id}")
async def get_dialog(conversation_id: str, response: Response, current_user: dict = Depends(get_current_user)):
    try:
        memberid=current_memberid(current_user)

        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()
        cursor.execute("""select a.request_text, b.response_text, a.imageurl
                       from request a
                       inner join response_claude b
                       on a.request_id=b.request_id and a.conversation_id=%s
                       inner join conversation c
                       on a.conversation_id=c.conversation_id and c.memberid=%s
                       order by a.id""",(conversation_id,memberid))
        result = cursor.fetchall()
        cursor.close()
        con.close()

        if result:
            return {"data": result}
        else:
            return {"error": True, "message": "dialog not found"}

    except Error as e:
        return {"error": True, "message": str(e)}

# https://docs.anthropic.com/en/docs/build-with-claude/vision
@app.post("/api/claude")
async def fetchopenai(response: Response, 
                      request_text: str = Form(...),
                      request_id: str = Form(...),
                      imageurl: Optional[str] = Form(None),
                      current_user: dict = Depends(get_current_user)):
    cursor = None
    con = None
    try:
        input_content = [{"type":"text","text":request_text}]
        
        if imageurl:
            extension_map = {
                'jpeg': 'jpg',
                'png': 'png'
            }
            image_type=imageurl.split('.')[-1]
            
            if image_type in extension_map:
                file_extension = extension_map[image_type]
                image1_media_type = "image/"+file_extension
                image1_data = base64.b64encode(httpx.get(imageurl).content).decode("utf-8")
                source={"type":"base64","media_type": image1_media_type,"data": image1_data,}
                input_content.append({"type":"image","source":source})

        message = client.messages.create(
            model="claude-3-5-sonnet-20240620", #claude-3-haiku-20240307
            max_tokens=1000,
            messages=[
                {"role": "user", "content": input_content}
            ]
        )

        res_text=message.content[0].text

        con = mysql.connector.connect(**db_config)
        cursor=con.cursor()

        if res_text:
            cursor.execute("""insert into response_claude(request_id,response_text) 
                           values(%s,%s)""",
                           (request_id,res_text))
            con.commit()
            response.status_code=200
            return {"ok": True, "message": "成功取得Claude response"}
        
    except Exception as e:
        response.status_code = 500
        print("Unexpected Error:", e)
        return {"error": True, "message": "An unexpected error occurred."}

    finally:
        if cursor is not None:
            cursor.close()
        if con is not None:
            con.close()


###################### speech to text
# from google.cloud import speech_v1
# from google.cloud import speech_v1p1beta1 as speech
from google.api_core.exceptions import GoogleAPIError
import logging
from google.cloud import speech
# from google.oauth2 import service_account

# Load credentials using the service account key file
# credentials = service_account.Credentials.from_service_account_file('focal-welder-433114-g7-350fbad7bbd9.json')

# Initialize Google Cloud Speech client with credentials
# client = speech.SpeechClient(credentials=credentials)

# 初始化 Google Cloud Speech 客戶端
client_record = speech.SpeechClient(
    client_options={
        'api_key': os.environ.get('SPEECH_TO_TEXT_KEY')
    }
)

# response沒有results解法：不要設定encoding，讓它自己去判斷
# https://cloud.google.com/speech-to-text/docs/release-notes?hl=zh-cn#v1beta1
@app.post("/api/recording")
async def convert_audio(file: UploadFile = File(...)):
    try:
        # Read the uploaded audio file
        audio_bytes = await file.read()
        
        # Set up Google Speech-to-Text API configuration
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            sample_rate_hertz=48000,  # Adjust if necessary, or use 44100 if recording with that sample rate
            language_code='zh-TW',
        )

        # Call Google Speech-to-Text API
        response = client_record.recognize(config=config, audio=audio)
        # print(response)

        # Extract transcription text
        transcription = ""
        for result in response.results:
            transcription += result.alternatives[0].transcript
        # print(transcription)

        return {"transcription": transcription}

    except GoogleAPIError as e:
        logging.error(f"Google API Error: {e}")
        return {"error": "An error occurred while processing the audio."}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": "An unexpected error occurred."}