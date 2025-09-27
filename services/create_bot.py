
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import logging
from .config import profiles_collection, urlzalo,save_file


def login(name: str,position=0):
    print(f" Bat dau Loginv1 tai khoan {name}")
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=480,540")
    options.add_argument(f"--window-position={position},0")
    options.add_argument(f"user-data-dir=E:/Zalo_crawls/.config/profile/{name}")     
    driver = webdriver.Chrome(options=options)
    driver.execute_script("document.body.style.zoom='50%'")
    driver.get(urlzalo)
    logging.info(f"Login tài khoản Zalo = {name}")
    time.sleep(8)
    pinner = driver.find_element(By.XPATH,"//div-16")
    driver.execute_script("arguments[0].click();", pinner)
    time.sleep(2)
    return driver

def create_profile():
    # Tìm id lớn nhất trong MongoDB
    last_profile = profiles_collection.find_one(sort=[("id", -1)])
    max_id = (last_profile["id"] + 1) if last_profile else 1
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir=E:/Zalo_crawls/.config/profile/{max_id}") 
    driver = webdriver.Chrome(options=options)
    driver.get(urlzalo)
    logging.info(f"Bat dau tao tai khoan zalo moi voi id {max_id}")
    while True:
        try:
            avatar = driver.find_element(By.XPATH, "//img[@class='a-child']")
            driver.execute_script("arguments[0].click();", avatar)
            time.sleep(1)
            name_profile = driver.find_element(By.XPATH, "//div-b18").text
            if name_profile:
                new_profile = {
                    "id": max_id,
                    "name": name_profile
                }
            profiles_collection.insert_one(new_profile)
            time.sleep(1)
            driver.close()
            logging.info(f"Tao thanh cong tai khoan id {max_id}")
            break
        except Exception:
            time.sleep(2)
            continue
    return 1
