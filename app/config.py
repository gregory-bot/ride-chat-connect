from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./waziride.db"

    # Pricing
    BASE_FARE_KES: float = 200
    PER_KM_KES: float = 60
    PER_MIN_KES: float = 4

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
    TWILIO_SMS_FROM: str = ""

    # Africa's Talking
    AT_USERNAME: str = "sandbox"
    AT_API_KEY: str = ""
    AT_SMS_SHORTCODE: str = ""

    # Geocoding
    GOOGLE_MAPS_API_KEY: str = ""


settings = Settings()
