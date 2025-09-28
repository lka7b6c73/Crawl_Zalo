from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse,JSONResponse
from services.create_bot import create_profile,login
from pydantic import BaseModel
from services import crawl
import threading
import logging
from services.config import *
from services.set import *
import os
drivers={}
threads = {}
stop_flags = {}
app = FastAPI()
app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/data/img", StaticFiles(directory="data/img"), name="img")
app.mount("/data/video", StaticFiles(directory="data/video"), name="video")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc thay bằng danh sách domain cụ thể như ["https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
used_x =[]
@app.get("/data/file/{filename}")
def download_file(filename: str):
    file_path = os.path.join(download_dir, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')

class NameRequest(BaseModel):
    name: str

@app.post("/create_profile")
def create_profile_endpoint():
    return create_profile()

@app.post("/login")
def login_user(data: NameRequest):
    name = data.name
    x = find_next_position(used_x)
    driver = login(name, x)
    drivers[name] = driver
    return {"message": f"Đã login user {name}"}

@app.post("/crawl")
def crawl_zalo(data: NameRequest):
    name = data.name
    if name in threads and threads[name].is_alive():
        return {"message": "Bot đang chạy rồi!"}

    profile = profiles_collection.find_one({'id': int(name)})
    if not profile:
        return {"error": "Không tìm thấy profile"}

    driver = drivers.get(name)
    if not driver:
        return {"error": "Chưa login tài khoản"}

    stop_event = threading.Event()
    stop_flags[name] = stop_event

    t = threading.Thread(target=crawl.run_bot, args=(driver, stop_event, profile['id'], profile['name']))
    t.start()
    threads[name] = t

    logging.info(f"Bot cho tài khoản {name} đã bắt đầu chạy")
    return {"message": f"Bot cho tài khoản {name} đã bắt đầu chạy"}

@app.post("/stop_crawl")
def stop_crawl(data: NameRequest):
    name = data.name
    stop_event = stop_flags.get(name)
    if not stop_event:
        return {"error": "Không có bot nào đang chạy"}
    stop_event.set()
    logging.info(f"Bot cho tài khoản {name} đã dừng")
    stop_flags.pop(name, None)
    threads.pop(name, None)
    return {"message": f"Bot của {name} đã được yêu cầu dừng"}

@app.post("/stop_bot")
def stop_bot(data: NameRequest):
    name = data.name
    driver = drivers.get(name)
    if not driver:
        return {"error": "Tài khoản chưa login hoặc bot không tồn tại"}
    try:
        driver.quit()
        logging.info(f"Đã dừng bot và đóng driver cho tài khoản {name}")
    except Exception as e:
        logging.error(f"Lỗi khi dừng bot tài khoản {name}: {e}")
        return {"error": f"Lỗi khi dừng bot: {e}"}
    drivers.pop(name, None)
    stop_flags.pop(name, None)
    threads.pop(name, None)
    return {"message": f"Bot cho tài khoản {name} đã dừng hoàn toàn"}
@app.get("/status_bot")
def status_bot():
    running_bots = [name for name, thread in threads.items() if thread.is_alive()]
    return {"running_bots": running_bots}

@app.post("/set_settings")
def change_settings(sett: bool):
    from services.config import settings
    settings = sett
    return {"settings": settings}

@app.get("/get_settings")
def get_settings():
    return {"settings": settings}


@app.get("/profiles")
def get_all_profiles():
    profiles = list(profiles_collection.find({}, {"_id": 0}))  # Loại bỏ field _id nếu không muốn
    return JSONResponse(content=profiles)

@app.get("/data")
def get_all_data():
    data = list(data_collection.find({}, {"_id": 0}))
    return JSONResponse(content=data)