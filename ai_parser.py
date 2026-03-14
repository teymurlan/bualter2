# Простейший AI Parser для голосовых и текстовых команд (можно интегрировать Gemini API)
def parse_command(command_text):
    command_text = command_text.lower()
    if "расход" in command_text:
        words = command_text.split()
        for w in words:
            if w.isdigit():
                return {"action": "add_expense", "amount": float(w)}
    elif "зарплата" in command_text:
        words = command_text.split()
        for w in words:
            if w.isdigit():
                return {"action": "pay_salary", "amount": float(w)}
    elif "заявка" in command_text:
        if "завершить" in command_text:
            return {"action": "complete_task"}
        elif "начать" in command_text:
            return {"action": "start_task"}
    return {"action": "unknown"}
