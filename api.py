import os
import base64
import hmac
import hashlib
import secrets
import time
from pathlib import Path
import pandas as pd
import sqlite3
import json
from pydantic import BaseModel
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "source" / "GGS.sqlite"
VARIABLES_DIR = DATA_DIR / "variables"
SHABADS_START_PATH = VARIABLES_DIR / "shabadsSTART.txt"
SHABADS_END_PATH = VARIABLES_DIR / "shabadsEND.txt"
SHABADS_UPDATED_PATH = VARIABLES_DIR / "shabadsUPDATED.txt"
SELECT_DIR = BASE_DIR / "select"
SELECT_USERNAME = os.getenv("SELECT_USERNAME", "sevadar")
SELECT_PASSWORD = os.getenv("SELECT_PASSWORD", "gursikh905")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production")
SESSION_COOKIE_NAME = "openhukamnama_session"
SESSION_MAX_AGE = 60 * 60 * 8

app.mount("/select", StaticFiles(directory=SELECT_DIR, html=True), name="select")


def replace_char_in_nested_json(data, target_char, replacement_char):
    if isinstance(data, dict):
        return {key: replace_char_in_nested_json(value, target_char, replacement_char) for key, value in data.items()}
    elif isinstance(data, list):
        return [replace_char_in_nested_json(element, target_char, replacement_char) for element in data]
    elif isinstance(data, str):
        return data.replace(target_char, replacement_char)
    else:
        return data


def create_session_token(username: str) -> str:
    expires_at = int(time.time()) + SESSION_MAX_AGE
    payload = f"{username}:{expires_at}"
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")


def verify_session_token(token: str | None) -> str | None:
    if not token:
        return None

    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        username, expires_at, signature = decoded.rsplit(":", 2)
    except (ValueError, UnicodeDecodeError):
        return None

    payload = f"{username}:{expires_at}"
    expected_signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not secrets.compare_digest(signature, expected_signature):
        return None

    if int(expires_at) < int(time.time()):
        return None

    return username


def require_authenticated_user(request: Request) -> str:
    username = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME))
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return username


@app.get("/")
def read_root():
    return RedirectResponse(url="/select/")


class LoginItem(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(item: LoginItem, response: Response):
    if not (
        secrets.compare_digest(item.username, SELECT_USERNAME)
        and secrets.compare_digest(item.password, SELECT_PASSWORD)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(item.username),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return {"authenticated": True}


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"authenticated": False}


@app.get("/session")
def session_status(request: Request):
    username = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME))
    return {"authenticated": bool(username)}


@app.get("/getShabads/{myPage}")
async def getShabads(myPage: int, _: str = Depends(require_authenticated_user)):
    cnx = sqlite3.connect(DATABASE_PATH)
    myQuery = f"SELECT * FROM shabads WHERE pageNum >= {myPage} AND pageNum <= {myPage + 1}"
    df = pd.read_sql_query(myQuery, cnx)
    payload = df[['id', 'pageNum', 'shabadP']]
    
    shabadsJSON = json.loads(payload.to_json(orient='records'))
    
    target_char = '&lt;&gt;'
    replacement_char = '<>'
    
    shabadsJSONnew = replace_char_in_nested_json(shabadsJSON, target_char, replacement_char)
    return(shabadsJSONnew)


@app.get("/updatedHukamnama")
def updated():
    with open(SHABADS_UPDATED_PATH, 'r') as file1:
        updated = file1.readlines()
    return {'updated':updated[0]}


@app.get("/hukamnama")
def hukamnama():
    with open(SHABADS_START_PATH, 'r') as file1:
        shabadStart = int(file1.readlines()[0])
    
    with open(SHABADS_END_PATH, 'r') as file1:
        shabadEnd = int(file1.readlines()[0])
    
    cnx = sqlite3.connect(DATABASE_PATH)
    myQuery = f"SELECT * FROM shabads WHERE id >= {shabadStart} AND id <= {shabadEnd}"
    df = pd.read_sql_query(myQuery, cnx)
    
    hukamnamaJSON = json.loads(df.to_json(orient='records'))
    page = str(hukamnamaJSON[0]['pageNum'])
    shabadEnglish = ''
    shabadPunjabi = ''
    for i in hukamnamaJSON:
        shabadEnglish = shabadEnglish +' '+ i['shabadE']
        shabadPunjabi = shabadPunjabi +' '+ i['shabadP']
    
    if len(shabadEnglish) > 1100:
        shabadEnglish = shabadEnglish[0:1100] + '...'
    if len(shabadPunjabi) > 700:
        shabadPunjabi = shabadPunjabi[0:700] + '...'
        
    return {'page':page,
            'shabadEnglish':shabadEnglish,
            'shabadPunjabi':shabadPunjabi.replace('&lt;&gt;','<>')
           }



class ShabadItem(BaseModel):
    firstShabad: str
    lastShabad: str

@app.post("/submit/")
async def submit_shabad(item: ShabadItem, _: str = Depends(require_authenticated_user)):
    from datetime import datetime
    import pytz
    with open(SHABADS_START_PATH, "w") as text_file:
        text_file.write(str(item.firstShabad))
    with open(SHABADS_END_PATH, "w") as text_file:
        text_file.write(str(item.lastShabad))
    
    tz = pytz.timezone('US/Eastern')  # EST timezone
    updated = "Last Updated - " + datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    with open(SHABADS_UPDATED_PATH, "w") as text_file:
        text_file.write(updated)
    return {"firstShabad": item.firstShabad, "lastShabad": item.lastShabad}
