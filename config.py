import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Токен бота от @BotFather
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Telegram-каналы для парсинга (без символа @)
    CHANNELS: list = ["vacanciesbest", "pstmarketing", "yojob"]
    
    # Сколько вакансий показывать
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "10"))

settings = Settings()
