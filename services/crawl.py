from selenium.webdriver.common.by import By
import time
from datetime import datetime, timedelta, timezone
import json 
import os
import base64
import requests
import logging
from .config import *
# Hàm này là để chuyển từ chưa đọc qua tất cả sẽ reload lại trang 
def reload(driver):
    # all
    all = driver.find_element(By.XPATH,"//div-b14[@data-translate-inner='STR_ALL']")
    driver.execute_script("arguments[0].click();", all)
    time.sleep(0.5)
    pinner = driver.find_element(By.XPATH,"//div-16")
    driver.execute_script("arguments[0].click();", pinner)
    time.sleep(0.5)
#unread
    unread = driver.find_element(By.XPATH,"//div-b14[@data-translate-inner='STR_UNREAD_LABEL']") 
    driver.execute_script("arguments[0].click();", unread)
#đây là ham kiểm tra xẻm có tin nhăn mới không 
def check_new_message(driver):
    try:
        mes_gr = driver.find_element(By.XPATH,"//div[@class='msg-item ']/div")
        return mes_gr
    except:
        return None
def convert_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M:%S - %d/%m/%Y")

def predict_time_from_id(id_number):
    # Chênh lệch quan sát được (~ -25 giây) từ các ví dụ trước
    time_offset = 25000  # 25 giây  
    # Thêm chênh lệch vào ID (số thứ hai)
    predicted_millis = int(id_number) + time_offset
    # Chuyển đổi mili giây thành thời gian thực với múi giờ UTC
    predicted_time = datetime.fromtimestamp(predicted_millis / 1000, timezone.utc)
    # Điều chỉnh theo múi giờ (Ví dụ múi giờ GMT+7)
    predicted_time += timedelta(hours=7)
    # Trả về thời gian dự đoán đã điều chỉnh
    return predicted_time.strftime('%Y-%m-%d %H:%M')
# cuộn trang xuống 
def scroll(driver):
    bb_mes = driver.find_element(By.XPATH,"//div[@id='messageViewContainer']/div")
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop - 1000;", bb_mes)

def download_img(driver, img_url,user,group):
    if img_url.startswith("blob:"): 
        # Tạo URL blob thành dữ liệu base64
        img_base64 = driver.execute_script("""
            return fetch(arguments[0])
                .then(res => res.blob())
                .then(blob => new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                }));
        """, img_url)
        # Giải mã dữ liệu từ base64
        header, encoded = img_base64.split(",", 1)
        file_extension = header.split(";")[0].split("/")[-1]
        image_data = base64.b64decode(encoded)
        # Trích xuất tên file từ blob URL
        file_name = img_url.split(":")[-1].split("/")[-1]  # Lấy '8733691f-bc6d-4bfa-995f-a099901a7dad'
        # Đường dẫn thư mục lưu ảnh
        group_dir = os.path.join(save_img, group)
        user_dir = os.path.join(group_dir, user)
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(user_dir, exist_ok=True)
        # Lưu ảnh vào thư mục con
        save_path = os.path.join(user_dir, f"{file_name}.{file_extension}")
        with open(save_path, "wb") as f:
            f.write(image_data)
        return f"{file_name}.{file_extension}"
    else:
        return "URL không hợp lệ hoặc không phải blob URL."


def download_video(driver,video_url,user,group):
    from .config import settings
    if settings:
    # Tách `id` từ URL video (blob URL hoặc URL thông thường)
        video_id = video_url.split(":")[-1].split("/")[-1]  # Lấy '8733691f-bc6d-4bfa-995f-a099901a7dad'
        file_name = f"{video_id}.mp4"
        # Tạo thư mục lưu video nếu chưa tồn tại
        group_dir = os.path.join(save_video, group)
        user_dir = os.path.join(group_dir, user)
        os.makedirs(user_dir, exist_ok=True)
        # Đường dẫn lưu video
        save_path = os.path.join(user_dir, file_name)
        # Tải video về
        result = driver.execute_async_script(f"""
        const callback = arguments[arguments.length - 1];
        fetch('{video_url}')
            .then(response => response.blob())
            .then(blob => {{
                const reader = new FileReader();
                reader.onloadend = function() {{
                    const base64data = reader.result.split(',')[1];
                    callback(base64data);
                }};
                reader.readAsDataURL(blob);
            }})
            .catch(err => callback('ERROR:' + err));
        """)
        with open(save_path, 'wb') as f:
            f.write(base64.b64decode(result))

    
      
def update_data(driver,list_bb_mes,id_group,name_gr,max_time,first_user_id,first_user_name):
    information = []
    data =[]
    file_data = []
    type1 = None
    type2 = None
    i = 0 
    # print("thu thập được",len(list_bb_mes))
    for bb_mes in reversed(list_bb_mes): # đoạn này xoay ngược lại cái list để thu thập từ dưới lên
        # đoạn này thì lấy thông tin nè
        bb_id = bb_mes.find_element(By.XPATH,".//div[@class='message-action']/div") # cái thẻ div có thuộc tính data-id 
        data_id = bb_id.get_attribute("data-id")
        if data_id is None:
            data_id = bb_id.get_attribute("data-qid")
        # cái số đầu tiên là id , 2 là thời gian, 3 là id user , 4 là id group
        # cái này chỉ có mỗi tin nhắn và hình ảnh có thôi

        # đoạn này là lấy time của box tin nhắn 
        full_time = bb_mes.get_attribute("id") # sẽ có dạng bb_msg_id_1737099761663
        time_id = int(full_time.split("_")[3]) # ta lấy mỗi cái id cuối thôi

        #giờ so sánh nếu cái time của tin nhắn hiện tại mà bé hơn hoặc bangừ cái max_time 
        # thì chứng tỏ là đây là tin nhắn đã crawl rồi
        # print(i,"so sanh time id",time_id ,"<>",max_time)
        if time_id <= max_time: 
            # print(i,"dừng lại giữa chừng vì",time_id ,"<=",max_time)
            if file_data:
                # print('file_data 1 ',file_data)
                if not type1:
                    type1 = first_user_id
                    type2 = first_user_name
                for file in file_data:     
                    file['user_id'] = type1
                    file['user_name'] = type2
                    data.append(file)
            return data, information
        
        i+=1
        
        ### message 
        if data_id and "ReceivedMsg_Text" in data_id:
            # Tách chuỗi bb_id_id để lấy các thành phần
            bb_id_id= bb_id.get_attribute("id")
            bb_id_text = bb_id.text
            parts = bb_id_id.split("-")
            type= parts[3]
            file_data.append({
                'id': parts[1],
                'type': 'message',
                'content': bb_id_text,
                'time': convert_timestamp(time_id),
                'user_id': parts[3],
                'group_id': id_group,
                'group_name': name_gr
            })
        ### photos
        elif data_id and "ReceivedMsg_Photo" in data_id:
 
            src = bb_id.find_element(By.XPATH,".//img").get_attribute("src")
            bb_id_id= bb_id.get_attribute("id")
            parts = bb_id_id.split("-")
            type= parts[3]
            try:
                text = bb_id.find_element(By.XPATH,".//span").text
            except:
                text = None
            file_data.append({
                'id': parts[1],
                'type': 'photo',
                'content': download_img(driver, src,parts[3],id_group),
                'text': text,
                'time': convert_timestamp(time_id),
                'user_id': parts[3],
                'group_id': id_group,
                'group_name': name_gr
            })
        ### info
        elif data_id and "DisabledTargetEventLayer" in data_id:
            info = bb_id.find_element(By.XPATH,".//div[@class='contact-card__info-container']").text 
            file_data.append({
                'type': 'info',
                'content': info,
                'time': convert_timestamp(time_id),
                'group_id':id_group,
                "group_name": name_gr
            })
        else:
            class_name = bb_id.get_attribute("class")
            ##file
            if 'file' in class_name:
        
                name = bb_id.find_element(By.XPATH,".//div-b14").get_attribute("title")
                size = bb_id.find_element(By.XPATH,".//span[@class='file-message__content-info-size']").text
                filed = bb_mes.find_element(By.XPATH,".//a")
                # driver.execute_script("arguments[0].click();", filed)
                file_data.append({
                    'type': 'file',
                    'content': name,
                    'size': size,
                    'time': convert_timestamp(time_id),
                    'user_id': None,
                    'group_id':id_group,
                    "group_name": name_gr
                })
            ###video
            elif 'video' in class_name:
                user_name = data_id.split("_")[1]# lấy ra user name của video từ thuộc tính crossorigin của thẻ img
                if not type:
                    type = user_name
                show_video = bb_mes.find_element(By.XPATH,".//div[@class='video-message__background-overlay video-message__background-overlay--clickable rounded-t-5 rounded-b-5']")
                driver.execute_script("arguments[0].click();", show_video)
                time.sleep(3)
                video_url = None
                while not video_url:
                    try:
                        time.sleep(0.5)
                        video_url= driver.find_element(By.XPATH,"//video").get_attribute("src")
                        uuid = video_url.split('/')[-1]
                        filevideo = f"{uuid}.mp4"
                    except:
                        pass
                download_video(driver,video_url,user_name,id_group)
                vclose = driver.find_element(By.XPATH,"//i[@class='btn dark btn--m  fa fa-close']")
                driver.execute_script("arguments[0].click();", vclose) # nhấn close để thoát khỏi trình show video
                file_data.append({
                    'type': 'video',
                    'content': filevideo,
                    'time': convert_timestamp(time_id),
                    'user_id': user_name,
                    'group_id':id_group,
                    "group_name": name_gr
                })
            elif 'group-photo' in class_name:
                a = bb_mes.find_elements(By.XPATH,".//div[@class='local-overlaying-message-status-wrapper']/div")
                for bb_id in a: 
                    bb_class = bb_id.get_attribute('class')
                    if "group-photo" in bb_class:
                        driver.execute_script("arguments[0].click();", bb_id)
                        video_url = None
                        time.sleep(3)
                        while not video_url:
                            try:
                                time.sleep(0.5)
                                video_url= driver.find_element(By.XPATH,"//video").get_attribute("src")
                                uuid = video_url.split('/')[-1]
                                filevideo = f"{uuid}.mp4"
                            except:
                                pass
                        bb_id_id= bb_id.get_attribute("id")
                        parts = bb_id_id.split("-")
                        type= parts[3]
                        # id_group = parts[-1]

                        download_video(driver,video_url,parts[3],id_group)
                        vclose = driver.find_element(By.XPATH,"//i[@class='btn dark btn--m  fa fa-close']")
                        driver.execute_script("arguments[0].click();", vclose)
                        # nhấn close để thoát khỏi trình show video

                        file_data.append({
                            'id': parts[1],
                            'type': 'video_in_album',
                            'content': filevideo,
                            'time': convert_timestamp(time_id),
                            'user_id': parts[3],
                            'group_id':id_group,
                            'group_name': name_gr
                        })
                    elif "picture" in bb_class:                                                                                                       
                        src = bb_id.find_element(By.XPATH,".//img").get_attribute("src")
                        bb_id_id= bb_id.find_element(By.XPATH,".//div").get_attribute("id")   
                        parts = bb_id_id.split("-")
                        type= parts[3]
                        # id_group = parts[-1]
                        file_data.append({
                            'id': parts[1],
                            'type': 'photo_in_album',
                            'content': download_img(driver, src,parts[3],id_group),
                            'time': convert_timestamp(time_id),
                            'user_id': parts[3],
                            'group_id': id_group,
                            'group_name': name_gr
                        })
        name_user = None
        # lấy name nguòi dùng nếu có
        try:
            name_user = bb_mes.find_element(By.XPATH,".//div[@class='truncate']").text
            # print('data name_user',name_user)
            # Tách chuỗi bb_id_id để lấy các thành phần
            bb_id_id= bb_id.get_attribute("id")
            parts = bb_id_id.split("-")

            information.append({
                'id': parts[3],
                'name':name_user
            })
            if file_data:
                if not type1: 
                    # print('no type')
                    type1 = parts[3]
                    type2 = name_user
                for file in file_data:     
                    file['user_id'] = type1
                    file['user_name'] = type2
                    data.append(file)
                file_data =[]
                type1 = None
                type2 = None

        except:
            pass

            # else:
            #     data.append({
            #         'type': 'mp3',
            #         'content': bb_id.text
            #     })
        # Sử dụng set để loại bỏ các phần tử trùng lặp
    if file_data:
        print('file_data 2 ',file_data)
        if not type1:
            type1 = first_user_id
            type2 = first_user_name
        for file in file_data:     
            file['user_id'] = type1
            file['user_name'] = type2
            data.append(file)
    
    return data, information

def update_information(new_info):
    # B1: Đảm bảo new_info không trùng id
    unique_data = {entry['id']: entry for entry in new_info}.values()
    new_info = list(unique_data)

    # B2: Lấy toàn bộ dữ liệu gốc từ MongoDB
    original_dict = {entry['id']: entry for entry in information_collection.find({}, {'_id': 0})}

    # B3: Duyệt và cập nhật
    for new_entry in new_info:
        _id = new_entry['id']
        if _id in original_dict:
            current_entry = original_dict[_id]
            current_name = current_entry.get('name')

            # Nếu có name mới và khác name hiện tại
            if new_entry.get('name') and new_entry['name'] != current_name:
                # Cập nhật lịch sử tên
                if 'history' not in current_entry:
                    current_entry['history'] = []
                current_entry['history'].append(current_name)

                # Cập nhật tên
                current_entry['name'] = new_entry['name']

            # Ghi lại vào MongoDB
            information_collection.update_one({"id": _id}, {"$set": current_entry})
        else:
            # Nếu chưa có entry, tạo mới
            if 'history' not in new_entry:
                new_entry['history'] = []
            information_collection.insert_one(new_entry)


def update_group(max_time, id_group, name_gr, first_user_id,first_user_name):
    # Kiểm tra xem nhóm đã tồn tại trong cơ sở dữ liệu chưa
    found = group_collection.find_one({"id": id_group})

    if found:
        # Nếu đã có nhóm trong MongoDB, kiểm tra sự thay đổi tên và cập nhật
        if found["name"] != name_gr:
            # Lưu tên cũ vào history nếu tên thay đổi
            if "history" not in found:
                found["history"] = []
            found["history"].append(found["name"])

        # Cập nhật các thông tin khác
        group_collection.update_one(
            {"id": id_group},
            {"$set": {
                "name": name_gr,
                "max_time": max_time,
                "first_user_id": first_user_id,
                "first_user_name": first_user_name
            }}
        )
    else:
        # Nếu nhóm chưa có, thêm mới
        group_collection.insert_one({
            "id": id_group,
            "name": name_gr,
            "max_time": max_time,
            "first_user_id": first_user_id,
            "first_user_name": first_user_name,
            "history": []  # Mới tạo nên không có history
        })

    return "Group updated successfully."
def count_by_type(data):
    type_counts = {}
    for item in data:
        type_value = item.get('type')
        if type_value:
            type_counts[type_value] = type_counts.get(type_value, 0) + 1
    return type_counts

def get_id_group(driver):
    while True:
        try:
            avatar = driver.find_element(By.XPATH,"//div[@class='rel zavatar-container']")
            driver.execute_script("arguments[0].click();", avatar)
            time.sleep(0.5)
            name_gr = driver.find_element(By.XPATH,"//div[@class='flx rel flx-al-c']/div").get_attribute("title")
            bb_mes = driver.find_element(By.XPATH,"//div[@class='stack-page']/div/div")
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop + 100;", bb_mes)
            time.sleep(0.5)
            link_gr = driver.find_element(By.XPATH,"//div[@class='pi-group-profile-link__link']").text
            group_id = link_gr.split("/")[-1]
            time.sleep(0.5)
            aa = driver.find_element(By.XPATH,"//i[@class='fa fa-close f16 pre']")
            driver.execute_script("arguments[0].click();", aa)
            return group_id,name_gr
        except: 
            aa = driver.find_element(By.XPATH,"//i[@class='fa fa-close f16 pre']")
            driver.execute_script("arguments[0].click();", aa)
        
    

def run_bot(driver,stop_event,profile_id,profile_name):   
    try:
        while not stop_event.is_set():
            #unread
            unread = driver.find_element(By.XPATH,"//div-b14[@data-translate-inner='STR_UNREAD_LABEL']")
            driver.execute_script("arguments[0].click();", unread)
            time.sleep(0.5)
            mes_gr= check_new_message(driver)
            if mes_gr:
                driver.execute_script("arguments[0].click();", mes_gr)
                time.sleep(1)
                id_group,name_gr = get_id_group(driver)
                group = list(group_collection.find({}, {'_id': 0}))
                #đoạn này là lấy max_time ra để chạy
                # max_time là thời gian của tin nhắn cuối cùng crawl được từ nhóm 
                max_time = next((item['max_time'] for item in group if item['id'] == id_group), None) # có gr avaf id rồ
                first_user_id = next((item['first_user_id'] for item in group if item['id'] == id_group), None) # có gr avaf id rồi
                first_user_name = next((item['first_user_name'] for item in group if item['id'] == id_group), None) # có gr avaf id rồi
                if max_time:
                    max_time = int(max_time) 
                else:
                    max_time = 0 # chưa cso gr 
            
                list_bb_mes = driver.find_elements(By.XPATH,"//div[@data-component='bubble-message']")
                # print(list_bb_mes[0].get_attribute("id").split("_"))
                try:
                    first_time = int(list_bb_mes[0].get_attribute("id").split("_")[3])
                except:
                    first_time = 0
                attempt =0
                while first_time > max_time and attempt < 1000:
                    attempt += 1
                    # print(first_time , max_time)
                    scroll(driver)
                    time.sleep(0.5)
                    list_bb_mes = driver.find_elements(By.XPATH,"//div[@data-component='bubble-message']")
                    first_time = int(list_bb_mes[0].get_attribute("id").split("_")[3])
                    time.sleep(0.5)
                    try:
                        overscroll = driver.find_element(By.XPATH,"//div[@class='flx-centralized']")
                        # print('here')
                        break 
                    except:
                        pass
                new_max_time = int(list_bb_mes[-1].get_attribute("id").split("_")[3]) # đoạn này lấy thời gian của tin nhắn cuối cùng
                # print("new_max_time",new_max_time,'max_time',max_time)
                #######
                new_data, new_info= update_data(driver,list_bb_mes,id_group,name_gr,max_time,first_user_id,first_user_name) # đoạn này craww
                ########
                first_user_id = next((item['user_id'] for item in new_data if 'user_id' in item), None) # đây là id cuôi cùng của người dùng trong nhóm
                first_user_name = next((item['user_name'] for item in new_data if 'user_id' in item), None) # đây là name cuôi cùng của người dùng trong nhóm
                for item in new_data:
                    item['profile_id'] = profile_id  # thay bằng giá trị cụ thể
                    item['profile_name'] = profile_name  # thay bằng giá trị cụ thể
                    t = item.get('type', '').lower()
                    if 'photo' in t:
                        item['url'] = f"/data/img/{item.get('group_id')}/{item.get('user_id')}/{item.get('content')}"
                    elif 'video' in t:
                        item['url'] = f"/data/video/{item.get('group_id')}/{item.get('user_id')}/{item.get('content')}"
                    elif 'file' in t:
                        item['url'] = f"/data/file/{item.get('content')}"
                update_group(new_max_time,id_group,name_gr,first_user_id,first_user_name) # đoạn này là cập nhật nhóm
                update_information(new_info)
                # đoạn này là nhảy ra cloud để tiến hành cập nhật lại data để tránh có tin nhắn mới vào làm ảnh hưởng
                all = driver.find_element(By.XPATH,"//div-b14[@data-translate-inner='STR_ALL']")
                driver.execute_script("arguments[0].click();", all)
                pinner = driver.find_element(By.XPATH,"//div-16")
                driver.execute_script("arguments[0].click();", pinner)

                if new_data:
                    data_collection.insert_many(new_data)
                logging.info(f"Bot: da thu thap duoc {count_by_type(new_data)} va {len(new_info)} user moi trong group {name_gr}") 
            else:  
                time.sleep(10)
                reload(driver)
    except Exception as e:
        print("Lỗi ngoài dự kiến trong bot:", e)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception as e:
            print("Lỗi khi đóng driver:", e)
        print("Bot đã dừng và driver đã được đóng.")