from pydantic import BaseModel, field_validator


class User(BaseModel):
    name: str
    id: int


class UserWithAge(BaseModel):
    name: str
    age: int


class Feedback(BaseModel):
    name: str
    message: str

    @field_validator('name')
    def validate_name(cls, value):
        if len(value) > 50:
            raise ValueError("Name should be less than 50 characters")
        elif len(value) < 2:
            raise ValueError("Name should contain at least 2 characters")
        return value

    @field_validator('message')
    def validate_message(cls, value: str):
        if len(value) > 500:
            raise ValueError("Message should be less than 500 characters")
        elif len(value) < 10:
            raise ValueError("Message should contain at least 10 characters")

        if any(word in value for word in ["кринж", "рофл", "вайб"]):
            raise ValueError("Использование недопустимых слов")
        return value

