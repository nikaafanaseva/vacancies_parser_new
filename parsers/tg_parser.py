import aiohttp
import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TGParser:
    """Парсер публичных Telegram-каналов через t.me/s/"""
    
    def __init__(self):
        self.base_url = "https://t.me/s/{}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    async def parse_channel(self, channel: str, query: str, limit: int = 10) -> list:
        """Парсит один канал"""
        results = []
        url = self.base_url.format(channel)
        
        try:
            logger.info(f"🔍 Парсинг @{channel} по запросу '{query}'")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=30) as resp:
                    if resp.status != 200:
                        logger.error(f"❌ @{channel}: HTTP статус {resp.status}")
                        return []
                    html_text = await resp.text()
            
            soup = BeautifulSoup(html_text, 'lxml')
            messages = soup.find_all("div", class_="tgme_widget_message_wrap")
            
            logger.info(f"📥 @{channel}: загружено {len(messages)} сообщений")
            
            for msg in messages:
                text_elem = msg.find("div", class_="tgme_widget_message_text")
                if not text_elem:
                    continue
                
                text = text_elem.get_text(separator='\n', strip=True)
                
                # Проверяем, есть ли запрос в тексте
                if query.lower() not in text.lower():
                    continue
                
                # Извлекаем данные
                title = self._extract_title(text)
                company = self._extract_company(text)
                salary = self._extract_salary(text)
                location = self._extract_location(text)
                
                # Ссылка на сообщение
                msg_link = msg.find("a", class_="tgme_widget_message_date")
                message_url = msg_link.get("href", "") if msg_link else f"https://t.me/{channel}"
                
                # Дата
                time_elem = msg.find("time", class_="datetime")
                date_str = ""
                if time_elem:
                    dt = time_elem.get("datetime", "")
                    if dt:
                        date_str = dt[:10]  # YYYY-MM-DD
                
                results.append({
                    "title": title,
                    "company": company,
                    "salary": salary,
                    "location": location,
                    "url": message_url,
                    "source": f"@{channel}",
                    "date": date_str
                })
                
                if len(results) >= limit:
                    break
                    
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга @{channel}: {e}", exc_info=True)
        
        logger.info(f"✅ @{channel}: найдено {len(results)} вакансий")
        return results

    def _extract_title(self, text: str) -> str:
        """Извлекает заголовок вакансии"""
        for line in text.split('\n'):
            line = line.strip()
            # Берём первую нормальную строку как заголовок
            if 5 < len(line) < 120:
                # Убираем эмодзи
                clean = re.sub(r'[^\w\s\-\(\)/.,:;!?а-яА-ЯёЁ]', '', line).strip()
                if clean and len(clean) > 3:
                    return clean[:100]
        return "Вакансия"

    def _extract_company(self, text: str) -> str:
        """Извлекает название компании"""
        patterns = [
            r'[Кк]омпания[:\s]+([^\n]+)',
            r'[Cc]ompany[:\s]+([^\n]+)',
            r'[Оо] компании[:\s]+([^\n]+)',
            r'[Рр]аботодатель[:\s]+([^\n]+)',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1).strip()[:50]
        return "Не указано"

    def _extract_salary(self, text: str) -> str:
        """Извлекает зарплату"""
        patterns = [
            r'(от\s*\d[\d\s]*(?:до\s*\d[\d\s]*)?(?:руб|₽|k|тыс|usd|\$)?)',
            r'(до\s*\d[\d\s]*(?:руб|₽|k|тыс|usd|\$)?)',
            r'(\d{1,3}(?:\s?\d{3})+\s*(?:руб|₽|k|тыс|usd|\$)?)',
            r'(\d+\s*[-–]\s*\d+\s*(?:руб|₽|k|тыс|usd|\$)?)',
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return "Не указано"

    def _extract_location(self, text: str) -> str:
        """Извлекает город"""
        cities = {
            "москва": "Москва",
            "санкт-петербург": "СПб",
            "спб": "СПб",
            "питер": "СПб",
            "казань": "Казань",
            "новосибирск": "Новосибирск",
            "екатеринбург": "Екатеринбург",
            "минск": "Минск",
            "удаленно": "Удалённо",
            "удалённо": "Удалённо",
            "remote": "Remote",
        }
        text_lower = text.lower()
        for key, name in cities.items():
            if key in text_lower:
                return name
        return "Не указано"

    async def search(self, channels: list, query: str, limit: int = 10) -> list:
        """Поиск по всем каналам"""
        all_results = []
        for channel in channels:
            try:
                results = await self.parse_channel(channel, query, limit)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Ошибка с каналом @{channel}: {e}")
                continue
        
        # Сортируем по дате (новые сначала)
        all_results.sort(key=lambda x: x.get("date", ""), reverse=True)
        return all_results[:limit]
