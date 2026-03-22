# app.py
# uvicorn app:app --reload

from fastapi import FastAPI, Query, HTTPException, Response, Cookie, Header, Request
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from itsdangerous import URLSafeSerializer
import uuid
import time
import datetime
import re

SECRET_KEY = "secret_key_1234567890"
serializer = URLSafeSerializer(SECRET_KEY)

SESSION_MAX_AGE = 300
SESSION_REFRESH_THRESHOLD = 180

app = FastAPI()

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = Field(None, gt=0)
    is_subscribed: bool = False
    password: str

class LoginData(BaseModel):
    username: str
    password: str


class Product(BaseModel):
    product_id: int
    name: str
    category: str
    price: float


class CommonHeaders(BaseModel):
    user_agent: str
    accept_language: str

    @validator('accept_language')
    def validate_accept_language(cls, v):
        pattern = r'^[a-zA-Z\-]+(?:,[a-zA-Z\-]+(?:;q=[0-1]\.[0-9])?)*$'
        if not re.match(pattern, v):
            raise ValueError('Invalid Accept-Language format')
        return v


users = {
    "user1": {
        "name": "Artem",
        "email": "Pochta@mail.ru",
        "age": 19,
        "is_subscribed": True,
        "password": "12345",
    },
    "user2": {
        "name": "Ne Artem",
        "email": "Ne_Pochta@mail.ru",
        "age": 24,
        "is_subscribed": False,
        "password": "54321",
    },
}

sample_products = [
    {"product_id": 123, "name": "Smartphone", "category": "Electronics", "price": 599.99},
    {"product_id": 456, "name": "Phone Case", "category": "Accessories", "price": 19.99},
    {"product_id": 789, "name": "Iphone", "category": "Electronics", "price": 1299.99},
    {"product_id": 101, "name": "Headphones", "category": "Accessories", "price": 99.99},
    {"product_id": 202, "name": "Smartwatch", "category": "Electronics", "price": 299.99},
]

@app.post("/create_user")
async def create_user(user_data: UserCreate):
    users["user"+str(len(user_data.name))] = {
        "name": user_data.name,
        "email": user_data.email,
        "age": user_data.age,
        "is_subscribed": user_data.is_subscribed,
        "password": user_data.password,
    }
    return user_data

@app.get("/users")
async def get_users():
    return users


@app.get("/product/{product_id}")
async def get_product(product_id: int):
    for product in sample_products:
        if product["product_id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/products/search")
async def search_products(
    keyword: str = Query(..., description="Keyword to search"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(10, description="Max results", ge=1, le=100)
):
    keyword_lower = keyword.lower()
    results = []
    for product in sample_products:
        if keyword_lower in product["name"].lower():
            if category:
                if product["category"].lower() == category.lower():
                    results.append(product)
            else:
                results.append(product)
    return results[:limit]


app.active_sessions = {}


def create_session_token(user_id: str, username: str) -> str:
    data = {
        "user_id": user_id,
        "username": username,
        "last_activity": int(time.time())
    }
    return serializer.dumps(data)


def validate_and_refresh_session(
        token: str,
        request: Request = None,
        response: Response = None) -> tuple[
            bool,
            Optional[dict],
            Optional[str]]:
    try:
        data = serializer.loads(token)
        user_id = data.get("user_id")
        username = data.get("username")
        last_activity = data.get("last_activity")

        if not all([user_id, username, last_activity]):
            return False, None, None

        stored_username = app.active_sessions.get(token)
        if stored_username != username:
            return False, None, None

        now = int(time.time())
        elapsed = now - last_activity

        if elapsed > SESSION_MAX_AGE:
            if token in app.active_sessions:
                del app.active_sessions[token]
            return False, None, None

        user_data = users.get(username)

        if elapsed >= SESSION_REFRESH_THRESHOLD and response and request:
            new_data = {
                "user_id": user_id,
                "username": username,
                "last_activity": now
            }
            new_token = serializer.dumps(new_data)

            del app.active_sessions[token]
            app.active_sessions[new_token] = username

            is_secure = request.url.scheme == "https"

            response.set_cookie(
                key="session_token",
                value=new_token,
                httponly=True,
                secure=is_secure,
                samesite="strict",
                max_age=SESSION_MAX_AGE,
                path="/"
            )

            return True, user_data, new_token

        return True, user_data, None

    except Exception:
        return False, None, None


@app.post("/login")
async def login(login_data: LoginData, request: Request, response: Response):
    user = users.get(login_data.username)
    if not user or user["password"] != login_data.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id = str(uuid.uuid4())
    session_token = create_session_token(user_id, login_data.username)

    app.active_sessions[session_token] = login_data.username

    is_secure = request.url.scheme == "https"

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=SESSION_MAX_AGE,
        path="/"
    )

    return {
        "message": "Login successful",
        "username": login_data.username,
        "user_id": user_id,
        "session_created": int(time.time()),
        "secure_cookie": is_secure,
        "samesite": "strict"
    }


@app.get("/user")
async def get_user(
        request: Request,
        response: Response,
        session_token: Optional[str] = Cookie(None)
):
    if not session_token:
        return Response(
            status_code=401,
            content='{"message": "Unauthorized"}',
            media_type="application/json"
        )

    is_valid, user_data, new_token = validate_and_refresh_session(session_token, request, response)

    if not is_valid:
        response.delete_cookie(key="session_token", path="/")
        return Response(
            status_code=401,
            content='{"message": "Unauthorized"}',
            media_type="application/json"
        )

    if new_token:
        data = serializer.loads(new_token)
    else:
        data = serializer.loads(session_token)

    return {
        "username": data["username"],
        "user_id": data["user_id"],
        "last_activity": data["last_activity"],
        "full_name": user_data["name"],
        "email": user_data["email"],
        "session_refreshed": new_token is not None
    }


@app.get("/headers")
async def get_headers(
        user_agent: Optional[str] = Header(None),
        accept_language: Optional[str] = Header(None)
):
    if not user_agent or not accept_language:
        return Response(
            status_code=400,
            content='{"message": "Missing required headers"}',
            media_type="application/json"
        )

    try:
        headers = CommonHeaders(
            user_agent=user_agent,
            accept_language=accept_language
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "User-Agent": headers.user_agent,
        "Accept-Language": headers.accept_language
    }


@app.get("/info")
async def get_info(
        response: Response,
        user_agent: Optional[str] = Header(None),
        accept_language: Optional[str] = Header(None)
):
    if not user_agent or not accept_language:
        return Response(
            status_code=400,
            content='{"message": "Missing required headers"}',
            media_type="application/json"
        )

    try:
        headers = CommonHeaders(
            user_agent=user_agent,
            accept_language=accept_language
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    current_time = datetime.datetime.now().isoformat()
    response.headers["X-Server-Time"] = current_time

    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": {
            "User-Agent": headers.user_agent,
            "Accept-Language": headers.accept_language
        }
    }
