# Тест GET-запроса к /user

import requests

session_1 = requests.Session()
session_1.post("http://localhost:8000/login", json={"username": "user1", "password": "12345"})
user_info_1 = session_1.get("http://localhost:8000/user")
print(user_info_1.json())

session_2 = requests.Session()
session_2.post("http://localhost:8000/login", json={"username": "user2", "password": "12345"})
user_info_2 = session_2.get("http://localhost:8000/user")
print(user_info_2.json())