from aiogram import Router
from aiogram.types import Message

router = Router()


@router.message()
async def handle_message(message: Message):
    await message.answer("Бот запущен и готов к работе.")
