from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


# ---------- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ РЯДОВ ----------

def _rows_from_buttons(buttons, per_row: int = 2):
    """
    Разбивает список кнопок на строки по per_row штук.
    """
    rows = []
    row = []
    for btn in buttons:
        row.append(btn)
        if len(row) >= per_row:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


# ---------- REPLY-КЛАВИАТУРА "МЕНЮ" (слева снизу) ----------

def main_menu_reply_keyboard():
    """
    Постоянная кнопка снизу слева: 'Меню'
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Меню")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# ---------- START MENU (INLINE) ----------

def start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Менеджмент", callback_data="section_management")],
            [InlineKeyboardButton(text="📁 Управление персоналом", callback_data="section_op")],
        ]
    )


# ---------- MANAGEMENT MENU ----------

def management_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❓ Вопросы (теория)", callback_data="mgmt_questions")],
            [InlineKeyboardButton(text="📊 Задачи (практика)", callback_data="mgmt_tasks")],
        ]
    )


# ---------- QUESTIONS MENU ----------

def questions_menu_keyboard():
    """
    Меню раздела вопросов:
    - список вопросов
    - тест на 5 вопросов (оценка знаний)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Список вопросов", callback_data="questions_list")],
            [InlineKeyboardButton(text="🧪 Оценка знаний (5 вопросов)", callback_data="quiz_start")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_management")],
        ]
    )


def questions_list_keyboard(questions: list):
    """
    questions: список словарей вида {"id": 1, "text": "..."}
    """
    buttons = [
        InlineKeyboardButton(
            text=f"Вопрос {q['id']}",
            callback_data=f"q_open_{q['id']}"
        )
        for q in questions
    ]

    rows = _rows_from_buttons(buttons, per_row=2)
    rows.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_questions_menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def question_actions_keyboard(question_id: int, show_answer_button: bool = True):
    """
    Клавиатура под вопросом:
    - до ответа: [Показать ответ] + [Следующий вопрос] + [К списку]
    - после ответа:       [Следующий вопрос] + [К списку]
    """
    rows = []

    if show_answer_button:
        rows.append(
            [InlineKeyboardButton(text="✅ Показать ответ", callback_data=f"q_answer_{question_id}")]
        )

    rows.append(
        [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data=f"q_next_{question_id}")]
    )
    rows.append(
        [InlineKeyboardButton(text="⬅️ К списку вопросов", callback_data="questions_list")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- TASKS MENU ----------

def tasks_menu_keyboard():
    """
    Меню раздела задач:
    - список задач
    (случайная задача убрана по твоему пункту 4)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Список задач", callback_data="tasks_list")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_management")],
        ]
    )


def tasks_list_keyboard(tasks: list):
    """
    tasks: список словарей вида {"id": 1, "text": "..."}
    """
    buttons = [
        InlineKeyboardButton(
            text=f"Задача {t['id']}",
            callback_data=f"task_{t['id']}"
        )
        for t in tasks
    ]

    rows = _rows_from_buttons(buttons, per_row=2)
    rows.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_tasks_menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def task_actions_keyboard(task_id: int, show_answer_button: bool = True):
    """
    Клавиатура под задачей:
    - до решения: [Показать решение] + [Следующая задача] + [К списку]
    - после решения:       [Следующая задача] + [К списку]
    (случайная задача убрана)
    """
    rows = []

    if show_answer_button:
        rows.append(
            [InlineKeyboardButton(text="✅ Показать решение", callback_data=f"task_answer_{task_id}")]
        )

    rows.append(
        [InlineKeyboardButton(text="➡️ Следующая задача", callback_data=f"task_next_{task_id}")]
    )
    rows.append(
        [InlineKeyboardButton(text="⬅️ К списку задач", callback_data="tasks_list")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)
