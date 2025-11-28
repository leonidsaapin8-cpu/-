from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.exceptions import TelegramBadRequest

from pathlib import Path
import random
import re

from .keyboards import (
    start_keyboard,
    management_keyboard,
    questions_menu_keyboard,
    questions_list_keyboard,
    question_actions_keyboard,
    tasks_menu_keyboard,
    tasks_list_keyboard,
    task_actions_keyboard,
    main_menu_reply_keyboard,
)

router = Router()

# =========================
#   ПУТИ И ФАЙЛЫ DATA/
# =========================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

QUESTIONS_FILE = DATA_DIR / "questions.txt"
TASKS_FILE = DATA_DIR / "tasks.txt"

IMG_PATTERN = re.compile(r"(img:[^\s]+)")
MAX_TG_MESSAGE = 4000  # безопасный лимит для текста


# =========================
#   ЗАГРУЗКА ВОПРОСОВ
# =========================

def load_questions():
    questions = []
    if not QUESTIONS_FILE.exists():
        print("⚠️ questions.txt не найден по пути:", QUESTIONS_FILE)
        return questions

    with QUESTIONS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) != 3:
                continue
            qid_str, q_text, q_answer = parts
            try:
                qid = int(qid_str)
            except ValueError:
                continue
            questions.append(
                {
                    "id": qid,
                    "text": q_text.strip(),
                    "answer": q_answer.strip(),
                }
            )
    questions.sort(key=lambda q: q["id"])
    print(f"❓ Загружено вопросов: {len(questions)}")
    return questions


# =========================
#   ЗАГРУЗКА ЗАДАЧ
# =========================

def load_tasks():
    tasks = []
    if not TASKS_FILE.exists():
        print("⚠️ tasks.txt не найден по пути:", TASKS_FILE)
        return tasks

    with TASKS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) != 3:
                continue
            tid_str, t_text, t_answer = parts
            try:
                tid = int(tid_str)
            except ValueError:
                continue
            tasks.append(
                {
                    "id": tid,
                    "text": t_text.strip(),
                    "answer": t_answer.strip(),
                }
            )
    tasks.sort(key=lambda t: t["id"])
    print(f"📊 Загружено задач: {len(tasks)}")
    return tasks


QUESTIONS = load_questions()
TASKS = load_tasks()

# Состояния теста знаний (пункт 3)
# { user_id: {"ids": [q_id1, ...], "index": 0, "correct": 0} }
QUIZ_STATES: dict[int, dict] = {}


# =========================
#    ВСПОМОГАТЕЛЬНЫЕ
# =========================

def split_text_and_images(raw: str):
    """
    Ищет в строке маркеры img:tables/....png
    Возвращает:
    - чистый текст без этих маркеров
    - список относительных путей к картинкам (например, "tables/table_01.png")
    """
    if not raw:
        return "", []

    images = []

    def replacer(match: re.Match):
        token = match.group(1)  # img:tables/table_01.png
        rel_path = token.split("img:")[1]  # tables/table_01.png
        images.append(rel_path)
        return ""  # удаляем маркер из текста

    clean_text = IMG_PATTERN.sub(replacer, raw).strip()
    return clean_text, images


async def send_photo(message_or_call, file_path: Path):
    """
    Отправка изображения с диска (aiogram 3: FSInputFile) через answer_photo.
    """
    photo = FSInputFile(path=str(file_path))
    if isinstance(message_or_call, Message):
        await message_or_call.answer_photo(photo)
    else:
        await message_or_call.message.answer_photo(photo)


async def send_long_text(send_func, text: str):
    """
    Отправляет текст кусками, чтобы не превышать лимит Телеграма.
    send_func — это message.answer или call.message.answer.
    """
    if not text:
        return

    for i in range(0, len(text), MAX_TG_MESSAGE):
        chunk = text[i : i + MAX_TG_MESSAGE]
        await send_func(chunk)


def get_next_question(current_id: int | None = None):
    """
    Возвращает следующий вопрос по id (по возрастанию, с циклом).
    Если current_id is None — вернёт первый.
    """
    if not QUESTIONS:
        return None

    ids = [q["id"] for q in QUESTIONS]
    ids.sort()

    if current_id is None:
        next_id = ids[0]
    else:
        try:
            idx = ids.index(current_id)
        except ValueError:
            next_id = ids[0]
        else:
            next_id = ids[(idx + 1) % len(ids)]

    return next((q for q in QUESTIONS if q["id"] == next_id), None)


def get_next_task(current_id: int | None = None):
    """
    Возвращает следующую задачу по id (по возрастанию, с циклом).
    """
    if not TASKS:
        return None

    ids = [t["id"] for t in TASKS]
    ids.sort()

    if current_id is None:
        next_id = ids[0]
    else:
        try:
            idx = ids.index(current_id)
        except ValueError:
            next_id = ids[0]
        else:
            next_id = ids[(idx + 1) % len(ids)]

    return next((t for t in TASKS if t["id"] == next_id), None)


# =========================
#          QUESTIONS
# =========================

async def send_question(message_or_call, question: dict):
    """
    Отправляет текст вопроса + клавиатуру действий.
    """
    q_text, q_images = split_text_and_images(question["text"])

    if isinstance(message_or_call, Message):
        send = message_or_call.answer
    else:
        send = message_or_call.message.answer

    header = f"Вопрос {question['id']}:"
    if q_text:
        full_text = f"{header}\n\n{q_text}"
    else:
        full_text = header

    await send_long_text(send, full_text)

    for img_rel_path in q_images:
        file_path = DATA_DIR / img_rel_path
        if file_path.exists():
            await send_photo(message_or_call, file_path)

    await send(
        "Выберите действие:",
        reply_markup=question_actions_keyboard(question["id"], show_answer_button=True),
    )


async def send_question_answer(call: CallbackQuery, question: dict):
    """
    Отправляет ответ на вопрос + картинки
    и под ответом рисует клавиатуру БЕЗ 'Показать ответ'.
    """
    ans_text, ans_images = split_text_and_images(question["answer"])

    header = f"Ответ на вопрос {question['id']}:"
    if ans_text:
        full_text = f"{header}\n\n{ans_text}"
    else:
        full_text = header

    await send_long_text(call.message.answer, full_text)

    for img_rel_path in ans_images:
        file_path = DATA_DIR / img_rel_path
        if file_path.exists():
            await send_photo(call, file_path)

    await call.message.answer(
        "Выберите действие:",
        reply_markup=question_actions_keyboard(question["id"], show_answer_button=False),
    )

    await call.answer()


# =========================
#            TASKS
# =========================

async def send_task(message_or_call, task: dict):
    """
    Отправляет условие задачи + картинки + клавиатуру действий.
    """
    q_text, q_images = split_text_and_images(task["text"])

    if isinstance(message_or_call, Message):
        send = message_or_call.answer
    else:
        send = message_or_call.message.answer

    header = f"Задача {task['id']}:"
    if q_text:
        full_text = f"{header}\n\n{q_text}"
    else:
        full_text = header

    await send_long_text(send, full_text)

    for img_rel_path in q_images:
        file_path = DATA_DIR / img_rel_path
        if file_path.exists():
            await send_photo(message_or_call, file_path)

    await send(
        "Выберите действие:",
        reply_markup=task_actions_keyboard(task["id"], show_answer_button=True),
    )


async def send_task_answer(call: CallbackQuery, task: dict):
    """
    Отправляет решение задачи + картинки
    и под решением рисует клавиатуру БЕЗ 'Показать решение'.
    """
    ans_text, ans_images = split_text_and_images(task["answer"])

    header = f"Решение задачи {task['id']}:"
    if ans_text:
        full_text = f"{header}\n\n{ans_text}"
    else:
        full_text = header

    await send_long_text(call.message.answer, full_text)

    for img_rel_path in ans_images:
        file_path = DATA_DIR / img_rel_path
        if file_path.exists():
            await send_photo(call, file_path)

    await call.message.answer(
        "Выберите действие:",
        reply_markup=task_actions_keyboard(task["id"], show_answer_button=False),
    )

    await call.answer()


# =========================
#      ТЕСТ ЗНАНИЙ (5 ВОПРОСОВ)
# =========================

async def quiz_send_question(call: CallbackQuery, user_id: int):
    state = QUIZ_STATES.get(user_id)
    if not state:
        await call.message.answer("Тест не найден. Запусти его заново.")
        return

    idx = state["index"]
    ids = state["ids"]
    total = len(ids)

    if idx >= total:
        await call.message.answer("Тест уже завершён.")
        return

    qid = ids[idx]
    question = next((q for q in QUESTIONS if q["id"] == qid), None)
    if not question:
        await call.message.answer("Вопрос теста не найден, пропускаем.")
        state["index"] += 1
        return await quiz_send_question(call, user_id)

    q_text, q_images = split_text_and_images(question["text"])

    header = f"🧪 Тест знаний\nВопрос {idx + 1} из {total}\n\nВопрос {qid}:"
    if q_text:
        full_text = f"{header}\n\n{q_text}"
    else:
        full_text = header

    await send_long_text(call.message.answer, full_text)

    for img_rel_path in q_images:
        file_path = DATA_DIR / img_rel_path
        if file_path.exists():
            await send_photo(call, file_path)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Показать ответ", callback_data=f"quiz_show_{qid}")],
            [InlineKeyboardButton(text="❌ Завершить тест", callback_data="quiz_cancel")],
        ]
    )

    await call.message.answer(
        "Когда будешь готов, нажми «Показать ответ».",
        reply_markup=kb,
    )


async def quiz_finish(call: CallbackQuery, user_id: int):
    state = QUIZ_STATES.pop(user_id, None)
    if not state:
        await call.message.answer("Тест не найден.")
        return

    total = len(state["ids"])
    correct = state["correct"]
    wrong = total - correct

    await call.message.answer(
        f"Тест завершён ✅\n"
        f"Правильных ответов: {correct}\n"
        f"Неправильных: {wrong}"
    )


async def quiz_register_answer(call: CallbackQuery, is_correct: bool):
    user_id = call.from_user.id
    state = QUIZ_STATES.get(user_id)
    if not state:
        await call.answer("Тест не найден.", show_alert=True)
        return

    if is_correct:
        state["correct"] += 1

    state["index"] += 1

    if state["index"] >= len(state["ids"]):
        await quiz_finish(call, user_id)
    else:
        await quiz_send_question(call, user_id)

    await call.answer()


# =========================
#         ХЕНДЛЕРЫ
# =========================

@router.message(Command("start"))
async def start_command(message: Message, command: CommandObject):
    """
    Обработка /start и deep-link /start <payload>.
    """
    payload = (command.args or "").strip()

    # включаем снизу кнопку "Меню" (reply-клавиатура)
    await message.answer(
        "Кнопка меню снизу 👇",
        reply_markup=main_menu_reply_keyboard(),
    )

    if payload:
        print(f"[START] payload = {payload!r}")

    # --- Распаковка payload ---

    # Сразу открыть меню вопросов
    if payload == "mgmt_questions":
        await message.answer(
            "Раздел ❓ Вопросы (теория).\nЧто тебе нужно?",
            reply_markup=questions_menu_keyboard(),
        )
        return

    # Сразу открыть меню задач
    if payload == "mgmt_tasks":
        await message.answer(
            "Раздел 📊 Задачи (практика).\nЧто выбираем?",
            reply_markup=tasks_menu_keyboard(),
        )
        return

    # Сразу открыть конкретную задачу: ?start=task_5
    if payload.startswith("task_"):
        try:
            tid = int(payload.split("_")[1])
        except (IndexError, ValueError):
            pass
        else:
            task = next((t for t in TASKS if t["id"] == tid), None)
            if task:
                await send_task(message, task)
                return

    # Сразу открыть конкретный вопрос: ?start=question_3
    if payload.startswith("question_"):
        try:
            qid = int(payload.split("_")[1])
        except (IndexError, ValueError):
            pass
        else:
            question = next((q for q in QUESTIONS if q["id"] == qid), None)
            if question:
                await send_question(message, question)
                return

    # Обычный /start или непонятный payload -> главное меню
    await message.answer(
        "Привет! Бот запущен ✅\nВыбери раздел:",
        reply_markup=start_keyboard(),
    )


# Кнопка "Меню" снизу (reply-клавиатура)
@router.message(F.text.casefold() == "меню")
async def menu_button_handler(message: Message):
    await message.answer(
        "Привет! Бот запущен ✅\nВыбери раздел:",
        reply_markup=start_keyboard(),
    )


# --- Главное меню (INLINE) ---

@router.callback_query(F.data == "section_management")
async def cb_section_management(call: CallbackQuery):
    await call.message.edit_text(
        "Раздел 🧠 Менеджмент.\nВыбери направление:",
        reply_markup=management_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "section_op")
async def cb_section_op(call: CallbackQuery):
    await call.message.edit_text(
        "Раздел 📁 Управление персоналом пока пуст 🙂",
        reply_markup=start_keyboard(),
    )
    await call.answer()


# ---------- ВОПРОСЫ (QUESTIONS) ----------

@router.callback_query(F.data == "mgmt_questions")
async def cb_mgmt_questions(call: CallbackQuery):
    await call.message.edit_text(
        "Раздел ❓ Вопросы (теория).\nЧто тебе нужно?",
        reply_markup=questions_menu_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "back_questions_menu")
async def cb_back_questions_menu(call: CallbackQuery):
    await call.message.edit_text(
        "Раздел ❓ Вопросы (теория).\nЧто тебе нужно?",
        reply_markup=questions_menu_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "questions_list")
async def cb_questions_list(call: CallbackQuery):
    if not QUESTIONS:
        await call.message.answer("Список вопросов пока пуст.")
        await call.answer()
        return

    short_q = [{"id": q["id"], "text": q["text"]} for q in QUESTIONS]
    kb = questions_list_keyboard(short_q)

    try:
        await call.message.edit_text(
            "Список вопросов:",
            reply_markup=kb,
        )
    except TelegramBadRequest:
        await call.message.answer(
            "Список вопросов:",
            reply_markup=kb,
        )

    await call.answer()


# ТЕСТ ЗНАНИЙ (пункт 3) — старт
@router.callback_query(F.data == "quiz_start")
async def cb_quiz_start(call: CallbackQuery):
    if not QUESTIONS:
        await call.message.answer("Пока нет вопросов для теста.")
        await call.answer()
        return

    user_id = call.from_user.id
    ids = [q["id"] for q in QUESTIONS]
    random.shuffle(ids)
    ids = ids[: min(5, len(ids))]  # максимум 5 вопросов

    QUIZ_STATES[user_id] = {"ids": ids, "index": 0, "correct": 0}

    await call.message.answer(
        "Запускаем тест знаний 🧪\n"
        "Тебе будет показано 5 вопросов (или меньше, если их меньше в базе).\n"
        "Отвечай сам, затем жми «Показать ответ» и оценивай, правильно ли ответил.",
    )

    await quiz_send_question(call, user_id)
    await call.answer()


@router.callback_query(F.data.startswith("quiz_show_"))
async def cb_quiz_show_answer(call: CallbackQuery):
    user_id = call.from_user.id
    state = QUIZ_STATES.get(user_id)
    if not state:
        await call.answer("Тест не найден.", show_alert=True)
        return

    try:
        qid = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        await call.answer("Некорректный id вопроса.", show_alert=True)
        return

    question = next((q for q in QUESTIONS if q["id"] == qid), None)
    if not question:
        await call.answer("Вопрос не найден.", show_alert=True)
        return

    ans_text, ans_images = split_text_and_images(question["answer"])

    idx = state["index"]
    total = len(state["ids"])
    header = f"Ответ на тестовый вопрос {idx + 1} из {total} (вопрос {qid}):"
    if ans_text:
        full_text = f"{header}\n\n{ans_text}"
    else:
        full_text = header

    await send_long_text(call.message.answer, full_text)

    for img_rel_path in ans_images:
        file_path = DATA_DIR / img_rel_path
        if file_path.exists():
            await send_photo(call, file_path)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Я ответил правильно", callback_data="quiz_right"),
                InlineKeyboardButton(text="❌ Я ответил неправильно", callback_data="quiz_wrong"),
            ],
            [InlineKeyboardButton(text="❌ Завершить тест", callback_data="quiz_cancel")],
        ]
    )

    await call.message.answer(
        "Оцени свой ответ:",
        reply_markup=kb,
    )

    await call.answer()


@router.callback_query(F.data == "quiz_right")
async def cb_quiz_right(call: CallbackQuery):
    await quiz_register_answer(call, is_correct=True)


@router.callback_query(F.data == "quiz_wrong")
async def cb_quiz_wrong(call: CallbackQuery):
    await quiz_register_answer(call, is_correct=False)


@router.callback_query(F.data == "quiz_cancel")
async def cb_quiz_cancel(call: CallbackQuery):
    QUIZ_STATES.pop(call.from_user.id, None)
    await call.message.answer("Тест прерван.")
    await call.answer()


# Открыть конкретный вопрос из списка
@router.callback_query(F.data.startswith("q_open_"))
async def cb_question_open(call: CallbackQuery):
    data = call.data  # q_open_5
    try:
        qid = int(data.split("_")[2])
    except (IndexError, ValueError):
        await call.answer("Некорректный id вопроса", show_alert=True)
        return

    question = next((q for q in QUESTIONS if q["id"] == qid), None)
    if not question:
        await call.answer("Вопрос не найден", show_alert=True)
        return

    await send_question(call, question)
    await call.answer()


# Показать ответ на вопрос
@router.callback_query(F.data.startswith("q_answer_"))
async def cb_question_answer(call: CallbackQuery):
    data = call.data  # q_answer_5
    try:
        qid = int(data.split("_")[2])
    except (IndexError, ValueError):
        await call.answer("Некорректный id вопроса", show_alert=True)
        return

    question = next((q for q in QUESTIONS if q["id"] == qid), None)
    if not question:
        await call.answer("Вопрос не найден", show_alert=True)
        return

    await send_question_answer(call, question)


# Следующий вопрос (пункт 5)
@router.callback_query(F.data.startswith("q_next_"))
async def cb_question_next(call: CallbackQuery):
    data = call.data  # q_next_5
    try:
        current_id = int(data.split("_")[2])
    except (IndexError, ValueError):
        current_id = None

    question = get_next_question(current_id)
    if not question:
        await call.answer("Вопросы не найдены", show_alert=True)
        return

    await send_question(call, question)
    await call.answer()


# ---------- ЗАДАЧИ (TASKS) ----------

@router.callback_query(F.data == "mgmt_tasks")
async def cb_mgmt_tasks(call: CallbackQuery):
    await call.message.edit_text(
        "Раздел 📊 Задачи (практика).\nЧто выбираем?",
        reply_markup=tasks_menu_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "back_to_management")
async def cb_back_to_management(call: CallbackQuery):
    await call.message.edit_text(
        "Раздел 🧠 Менеджмент.\nВыбери направление:",
        reply_markup=management_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "back_tasks_menu")
async def cb_back_tasks_menu(call: CallbackQuery):
    await call.message.edit_text(
        "Раздел 📊 Задачи (практика).\nЧто выбираем?",
        reply_markup=tasks_menu_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "tasks_list")
async def cb_tasks_list(call: CallbackQuery):
    if not TASKS:
        await call.message.answer("Список задач пока пуст.")
        await call.answer()
        return

    short_tasks = [{"id": t["id"], "text": t["text"]} for t in TASKS]
    kb = tasks_list_keyboard(short_tasks)

    try:
        await call.message.edit_text(
            "Список задач:",
            reply_markup=kb,
        )
    except TelegramBadRequest:
        await call.message.answer(
            "Список задач:",
            reply_markup=kb,
        )

    await call.answer()


# Открыть задачу
@router.callback_query(F.data.regexp(r"^task_\d+$"))
async def cb_task_open(call: CallbackQuery):
    data = call.data  # task_5
    try:
        tid = int(data.split("_")[1])
    except (IndexError, ValueError):
        await call.answer("Некорректный id задачи", show_alert=True)
        return

    task = next((t for t in TASKS if t["id"] == tid), None)
    if not task:
        await call.answer("Задача не найдена", show_alert=True)
        return

    await send_task(call, task)
    await call.answer()


# Показать решение задачи
@router.callback_query(F.data.startswith("task_answer_"))
async def cb_task_answer(call: CallbackQuery):
    data = call.data  # task_answer_5
    try:
        tid = int(data.split("_")[2])
    except (IndexError, ValueError):
        await call.answer("Некорректный id задачи", show_alert=True)
        return

    task = next((t for t in TASKS if t["id"] == tid), None)
    if not task:
        await call.answer("Задача не найдена", show_alert=True)
        return

    await send_task_answer(call, task)


# Следующая задача (пункт 5)
@router.callback_query(F.data.startswith("task_next_"))
async def cb_task_next(call: CallbackQuery):
    data = call.data  # task_next_5
    try:
        current_id = int(data.split("_")[2])
    except (IndexError, ValueError):
        current_id = None

    task = get_next_task(current_id)
    if not task:
        await call.answer("Задачи не найдены", show_alert=True)
        return

    await send_task(call, task)
    await call.answer()


# =========================
#  РЕГИСТРАЦИЯ РОУТЕРА
# =========================

def register_handlers(dp):
    dp.include_router(router)
