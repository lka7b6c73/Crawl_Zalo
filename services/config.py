from pymongo import MongoClient
import logging
import os
client = MongoClient("mongodb://localhost:27017")
db = client["zalo"]
profiles_collection = db["profile"]
data_collection = db["data"]
information_collection = db["information"]
group_collection = db["group"]
settings = True
urlzalo = "https://id.zalo.me/account?continue=https%3A%2F%2Fchat.zalo.me%2F"
save_img = 'E:/Zalo_crawls/data/img'
save_video = 'E:/Zalo_crawls/data/video'
save_file = 'E:/Zalo_crawls/data/file'
url_gr = "https://zalo.me/g/"
download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
# Cấu hình logger
logging.basicConfig(
    filename='crawl.log',
    filemode='a',  # hoặc 'w' nếu muốn ghi đè
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Có thể đổi thành DEBUG nếu cần log chi tiết hơn
)