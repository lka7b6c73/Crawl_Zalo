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

@app.post("/crawls")
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




from fastapi import Query
import re
@app.get("/crawl_group")
def crawl_group_endpoint(id: str = Query(...), group: str = Query(...)):
    # Kiểm tra driver tương ứng idbot đang có
    driver = drivers.get(id)
    if not driver:
        raise HTTPException(status_code=400, detail="Tài khoản bot chưa login hoặc không tồn tại")

    # Khởi động crawl_group trong thread để không block request (nếu bạn muốn đồng bộ thì bỏ threading)
    stop_event = threading.Event()
    profile = profiles_collection.find_one({'id': int(id)})
    def crawl_and_store():
        try:
            # Gọi hàm crawl mất thời gian tùy bạn định nghĩa
            crawl.crawl_group(driver, group,id, profile['name'])
        except Exception as e:
            logging.error(f"Lỗi crawl group {group}: {e}")

    t = threading.Thread(target=crawl_and_store)
    t.start()

    # Đợi crawl hoàn thành hoặc trả lời trước nếu muốn
    t.join()  # Nếu muốn chờ crawl xong mới trả về dữ liệu
    # Hoặc bỏ nếu muốn trả về ngay
    grid = group
    group = group_collection.find_one({"id": grid}, {
        "_id": 0,
        "id": 1,
        "name": 1,
        "url": 1,
        "len_gr": 1,
        "last_crawl": 1
    })
    if not group:
        raise HTTPException(status_code=404, detail="Đã yêu cầu tham gia hoặc chưa được xác nhận")

    # Lấy dữ liệu tin nhắn
    messages_cursor = data_collection.find({"group_id": grid}, {
        "_id": 0,
        "id": 1,
        "type": 1,
        "content": 1,
        "time": 1,
        "user_id": 1,
        "user_name": 1,
        "url":1
    })

    messages = []
    for mes in messages_cursor:
        messages.append({
            "id_mes": mes.get("id", None),
            "type": mes.get("type", None),
            "content": mes.get("content", None),
            "time": mes.get("time", None),
            "id_user": mes.get("user_id", None),
            "name_user": mes.get("user_name", None),
            "url": mes.get("url", None),
        })

    return JSONResponse(content={
        "id_group": group.get("id", None),
        "name_group": group.get("name", None),
        "len_group": group.get("len_gr", None),
        "url_group": group.get("url", None),
        "last_crawl": group.get("last_crawl", None),
        "data": messages,
    })