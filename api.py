import os
from pathlib import Path
import pandas as pd
import sqlite3
import json
from pydantic import BaseModel
from fastapi import FastAPI
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


@app.get("/")
def read_root():
    return RedirectResponse(url="/select/")


@app.get("/select-config")
def select_config():
    return {
        "username": SELECT_USERNAME,
        "password": SELECT_PASSWORD,
    }


@app.get("/getShabads/{myPage}")
async def getShabads(myPage: int):
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
async def submit_shabad(item: ShabadItem):
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
