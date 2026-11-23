"""Контракты нового Auth API, заданные в техническом задании."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RegisterBody(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=5, max_length=32)
    password: str = Field(min_length=12, max_length=128)
    password_confirm: str
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    patronymic: str | None = Field(default=None, max_length=100)
    agree_to_terms: bool

    @model_validator(mode="after")
    def check_confirmation_and_terms(self):
        if self.password != self.password_confirm:
            raise ValueError("password and password_confirm must match")
        if not self.agree_to_terms:
            raise ValueError("agree_to_terms must be true")
        return self


class DeviceInfo(BaseModel):
    user_agent: str | None = Field(default=None, max_length=512)
    ip: str | None = Field(default=None, max_length=64)
    device_name: str | None = Field(default=None, max_length=100)


class LoginBody(BaseModel):
    login: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    device_info: DeviceInfo = Field(default_factory=DeviceInfo)


class LogoutBody(BaseModel):
    logout_all_devices: bool = False


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)
    new_password_confirm: str

    @model_validator(mode="after")
    def check_confirmation(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError("new_password and new_password_confirm must match")
        return self


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token_from_email: str = Field(min_length=6, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)
    new_password_confirm: str

    @model_validator(mode="after")
    def check_confirmation(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError("new_password and new_password_confirm must match")
        return self


class VerifyBody(BaseModel):
    type: Literal["email", "phone"]
    code: str = Field(pattern=r"^\d{6}$")


class ResendCodeBody(BaseModel):
    type: Literal["email", "phone"]


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    patronymic: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    business_description: str | None = Field(default=None, max_length=200)
    notification_preferences: dict[str, bool] | None = None


class IdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    phone: str
    first_name: str
    last_name: str
    patronymic: str | None
    avatar: str | None
    business_description: str | None
    notification_preferences: dict[str, bool]
    email_verified: bool
    phone_verified: bool
    role: str
    created_at: datetime


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
