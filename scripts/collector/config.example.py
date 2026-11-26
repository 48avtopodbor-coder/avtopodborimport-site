"""Параметры каталога для локального config.py."""

import datetime
import os

TARGET_BRANDS = [{'name_cn': '哈弗', 'name_ru': 'Haval', 'slug': 'hafu'},
 {'name_cn': '吉利汽车', 'name_ru': 'Geely', 'slug': 'jiliqiche'},
 {'name_cn': '奇瑞', 'name_ru': 'Chery', 'slug': 'qirui'},
 {'name_cn': '长安', 'name_ru': 'Changan', 'slug': 'changan'},
 {'name_cn': '比亚迪', 'name_ru': 'BYD', 'slug': 'biyadi'},
 {'name_cn': '理想汽车', 'name_ru': 'Li Auto', 'slug': 'lixiangqiche'},
 {'name_cn': '坦克', 'name_ru': 'Tank', 'slug': 'tanke'},
 {'name_cn': '星途', 'name_ru': 'Exeed', 'slug': 'xingtu'},
 {'name_cn': '极氪', 'name_ru': 'Zeekr', 'slug': 'jike'},
 {'name_cn': '奔驰', 'name_ru': 'Mercedes-Benz', 'slug': 'benchi'},
 {'name_cn': '现代', 'name_ru': 'Hyundai', 'slug': 'xiandai'},
 {'name_cn': '起亚', 'name_ru': 'Kia', 'slug': 'qiya'},
 {'name_cn': '斯柯达', 'name_ru': 'Skoda', 'slug': 'sikeda'},
 {'name_cn': '丰田', 'name_ru': 'Toyota', 'slug': 'fengtian'},
 {'name_cn': '大众', 'name_ru': 'Volkswagen', 'slug': 'dazhong'},
 {'name_cn': '宝马', 'name_ru': 'BMW', 'slug': 'baoma'},
 {'name_cn': '奥迪', 'name_ru': 'Audi', 'slug': 'aodi'},
 {'name_cn': '捷达', 'name_ru': 'Jetta', 'slug': 'jieda'},
 {'name_cn': '马自达', 'name_ru': 'Mazda', 'slug': 'mazida'}]

SUBBRAND_RULES = [{'keywords': ('OMODA', '欧萌达'),
  'name_cn': '欧萌达',
  'name_ru': 'Omoda',
  'parent': 'Chery'}]

AGE_FILTER = 'a3_5'

DELAY_MIN = 2.0

DELAY_MAX = 5.0

MAX_PAGES_PER_BRAND = 10

FETCH_ATTEMPTS = 8

UPDATE_PAGES = 2

CHE168_MIN_INTERVAL = (5, 10)

CHE168_COOLDOWN_MIN = 90

API_INTERVAL = (1.0, 2.0)

# Возраст 3–5 лет по году, как в действующем сборщике.
MIN_YEAR = datetime.date.today().year - 5
MAX_YEAR = datetime.date.today().year - 3
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cars.db")
