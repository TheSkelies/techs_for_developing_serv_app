# app.py
# uvicorn app:my_app --reload
from fastapi import FastAPI
from fastapi.responses import FileResponse
from models import User, UserWithAge, Feedback

my_app = FastAPI()

# 1.2
@my_app.get('/')
async def root():
    return FileResponse(path='index.html')


# 1.3
@my_app.post("/calculate")
async def calculate(num1: int, num2: int):
    return {"result": num1 + num2}

# 1.4
users = [
    User(name="Илюхин Артём Дмитриевич", id=1),
    User(name="кто-то ктотович ктотов", id=2)
]

@my_app.get("/users")
async def all_users():
    return users

@my_app.get('/users/{user_id}')
async def get_user(user_id: int):
    for user in users:
        if user.id == user_id:
            return user
    return {"Error": "User not found"}


# 1.5
@my_app.post("/users_with_age")
async def is_user_adult(user: UserWithAge):
    if user.age >= 18:
        return {
            "name": user.name,
            "age": user.age,
            "is_adult": True
        }
    else:
        return {
            "name": user.name,
            "age": user.age,
            "is_adult": False
        }


# 2.1 и 2.2
feedbacks = []

@my_app.post("/feedback")
async def feedback(fb: Feedback):
    feedbacks.append(fb)
    return {"message": f"Спасибо, {fb.name}! Ваш отзыв сохранён."}

@my_app.get("/feedbacks")
async def get_feedbacks():
    return feedbacks
