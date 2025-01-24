import asyncio
import telegram
import time


class TGbot:
    def __init__(self):
        self.chat_id_list = ["7376656100", "1244964129"]
        self.bot = telegram.Bot(
            "7206924017:AAG7RYQriBlnWfiFFe9FuuT8ox_wYlKSKoc")

    async def send_message(self, message):
        print("heya")
        async with self.bot:
            for chat_id in self.chat_id_list:
                await self.bot.sendMessage(chat_id=chat_id, text=message)


# tgbot = TGbot()
# asyncio.run(tgbot.send_message("123123123"))
