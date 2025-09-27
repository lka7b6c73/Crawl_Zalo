from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse,JSONResponse
from services.create_bot import create_profile,login
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

used_x =[]
@app.get("/data/file/{filename}")
def download_file(filename: str):
    file_path = os.path.join(download_dir, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')

@app.get("/create_profile")
def create_profile_endpoint():
    return create_profile()

@app.get("/login")
def login_user(name: str):
    x = find_next_position(used_x)
    driver = login(name,x)
    drivers[name] = driver
    return {"message": f"Đã login user {name}"}

@app.get("/crawl")
def crawl_zalo(name: str):
    if name in threads and threads[name].is_alive():
        return {"message": "Bot đang chạy rồi!"}
    profile = profiles_collection.find_one({'id': int(name)})

    driver = drivers.get(name)
    if not driver:
        return {"error": "Chưa login tài khoản"}

    # Tạo stop_flag mới cho tài khoản
    stop_event = threading.Event()
    stop_flags[name] = stop_event

    # Tạo thread chạy bot
    t = threading.Thread(target=crawl.run_bot, args=(driver, stop_event,profile['id'],profile['name']))
    t.start()
    threads[name] = t
    
    logging.info(f"Bot cho tai khoan {name} da bat dau chay")
    return {"message": f"Bot cho tài khoản {name} đã bắt đầu chạy"}

@app.get("/stop_crawl")
def stop_crawl(name: str):
    stop_event = stop_flags.get(name)
    if not stop_event:
        return {"error": "Không có bot nào đang chạy"}
    stop_event.set()  # Ra lệnh dừng
    logging.info(f"Bot cho tai khoan {name} da stop")
    stop_flags.pop(name,None)
    threads.pop(name, None)
    return {"message": f"Bot của {name} đã được yêu cầu dừng"}

@app.get("/stop_bot")
def stop_bot(name: str):
    driver = drivers.get(name)
    if not driver:
        return {"error": "Tài khoản chưa login hoặc bot không tồn tại"}

    try:
        driver.quit()  # Đóng trình duyệt, dừng driver
        logging.info(f"Đã dừng bot và đóng driver cho tài khoản {name}")
    except Exception as e:
        logging.error(f"Lỗi khi dừng bot tài khoản {name}: {e}")
        return {"error": f"Lỗi khi dừng bot: {e}"}

    # Xóa driver và các trạng thái liên quan
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