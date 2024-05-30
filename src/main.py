#!/usr/bin/python3

import requests
import json
import time
import os
from enum import Enum

class TelegramBot:
    def __init__(self, token, chat_id):
        self.url = 'https://api.telegram.org/bot{token}/'.format(
            token=token
        )
        self.chat_id = chat_id
    def send_message(self, text: str) -> bool:
        payload = {'chat_id': self.chat_id, 'text': text}
        r = requests.post(self.url+'sendMessage', json=payload)
        if r.status_code == 200:
            return True


class BotConfig:
    def __init__(self, token, channel_id):
        self.token = token
        self.channel_id = channel_id

class Schedule(Enum):
    UNKNOWN=0
    DAY=1
    ALL=2
    NIGHT=3

class Fairy:
    def __init__(self, name, schedule):
        self.name = name
        self.schedule = schedule

date = None

def load_config():
    with open('config.json') as f:
        j = json.load(f)
        return BotConfig(j['token'], j['channel_id'])

def fetch_items():
    url = 'https://shop.ichefpos.com/api/graphql/online_restaurant?op=restaurantMenuItemCategoriesQuery'
    response = requests.post(
        url, 
        headers={"Content-Type": "application/json", "cache-control": "no-cache"},
        json={"operationName":"restaurantMenuItemCategoriesQuery","variables":{"publicId":"WqxdHUPa"},"query":"query restaurantMenuItemCategoriesQuery($publicId: String) {\n restaurant(publicId: $publicId) {\n menu {\n categoriesSnapshot {\n uuid\n _id: uuid\n name\n menuItemSnapshot {\n ...restaurantMenuItemBasicFields\n __typename\n }\n __typename\n }\n __typename\n }\n __typename\n }\n}\n\nfragment restaurantMenuItemBasicFields on OnlineRestaurantMenuItemSnapshotOutput {\n _id: uuid\n uuid\n ichefUuid\n name\n price\n pictureFilename\n menuItemType\n description\n isSoldOut\n __typename\n}\n"})
    return response.json()

def parse_items(items):
    try:
        global date
        fairies = []
        for item in items['data']['restaurant']['menu']['categoriesSnapshot']:
            schedule_name = item['name']
            date = schedule_name[:8]
            schedule = Schedule.UNKNOWN
            if "午晚安" in schedule_name:
                schedule = Schedule.ALL
            elif "午安" in schedule_name:
                schedule = Schedule.DAY
            else:
                schedule = Schedule.NIGHT

            for menuItem in item['menuItemSnapshot']:
                fairy = Fairy(menuItem['name'], schedule)
                fairies.append(fairy)

            fairies.sort(key=lambda x: x.schedule.value)
        return fairies
                
    except Exception as e:
        print("Error parsing items")
        print(e)
    return []

def start(bot):
    items = fetch_items()
    fairies = parse_items(items)
    global date
    message = f"{date} 出勤的小精靈有：\n\n"
    for fairy in fairies:
        emoji = ""
        if fairy.schedule == Schedule.DAY:
            emoji = "☀️"
        elif fairy.schedule == Schedule.ALL:
            emoji = "🌍"
        else:
            emoji = "🌙"
        message += f"{fairy.name} {emoji}\n"
    bot.send_message(text=message)

    # Write today to records
    with open('record.json', 'w') as f:
        json.dump({"date": date}, f)

def checkNeedStart():
    if not os.path.exists('record.json'):
        return True
    with open('record.json') as f:
        record = json.load(f)
        if record['date'] != time.strftime("%Y%m%d"):
            return True
    return False

def main():
    botConfig = load_config()
    bot = TelegramBot(botConfig.token, botConfig.channel_id)
    while True:
        hour = time.strftime("%H")
        minute = time.strftime("%M")
        if checkNeedStart() and int(hour) == 14 and int(minute) < 20:
            start(bot)
        print(f"Sleeping... {hour}:{minute}")
        time.sleep(60)

if __name__ == '__main__':
    main()