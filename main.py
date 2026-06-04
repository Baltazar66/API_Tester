import flet as ft
import requests
import os
import json
from tkinter import Tk, filedialog

def main(page: ft.Page):
    page.title = "API Tester"
    page.window_width = 550
    page.window_height = 600

    # ---- Поля для URL ----
    base_url_field = ft.TextField(label="Базовый URL", width=420,
                                  value="https://test-api-eosago.renins.com")
    endpoint_field = ft.TextField(label="Путь (endpoint)", width=420,
                                  value="/calculate/")  # пример, можно оставить пустым

    # ---- Метод запроса ----
    method_dropdown = ft.Dropdown(
        label="Метод",
        width=100,
        value="GET",
        options=[
            ft.dropdown.Option("GET"),
            ft.dropdown.Option("POST"),
            ft.dropdown.Option("PUT"),
            ft.dropdown.Option("DELETE"),
        ],
    )

       # ---- Авторизация API Key (Query) ----
    api_key_name = ft.TextField(label="Имя параметра (key)", width=200, value="key")
    api_key_value = ft.TextField(label="Значение ключа", width=300, password=True,
    value="SECRET_KEY_DEMO")  # сразу подставим демо-ключ

    # ---- Выбор файла с данными (для POST/PUT) ----
    selected_file_label = ft.Text("Файл не выбран", italic=True)

    def pick_file_dialog(e):
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename()
        root.destroy()
        if file_path:
            selected_file_label.value = file_path
        else:
            selected_file_label.value = "Файл не выбран"
        page.update()

 
    # ---- Область ответа ----
    response_area = ft.TextField(
        label="Ответ сервера",
        multiline=True,
        min_lines=6,
        max_lines=12,
        read_only=True,
        width=500,
    )

    # ---- Отправка запроса ----
    def send_request(e):
        base = base_url_field.value.strip().rstrip("/")
        endpoint = endpoint_field.value.strip()
        if not base:
            response_area.value = "Введите базовый URL"
            page.update()
            return

        if endpoint:
            url = base + "/" + endpoint.lstrip("/")
        else:
            url = base

        method = method_dropdown.value
        headers = {}

        file_path = selected_file_label.value
        form_data = {}

        if file_path and file_path != "Файл не выбран" and os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                json_obj = json.loads(content)

                def flatten_json(obj, parent_key=''):
                    items = {}
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            new_key = f"{parent_key}[{k}]" if parent_key else k
                            items.update(flatten_json(v, new_key))
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj):
                            new_key = f"{parent_key}[{i}]"
                            items.update(flatten_json(v, new_key))
                    else:
                        items[parent_key] = str(obj) if not isinstance(obj, str) else obj
                    return items

                form_data = flatten_json(json_obj)
                form_data["key"] = api_key_value.value
            except Exception as ex:
                response_area.value = f"Ошибка разбора файла: {ex}"
                page.update()
                return
        else:
            response_area.value = "Выберите файл с данными"
            page.update()
            return

        try:
            resp = requests.post(url, headers=headers, data=form_data, timeout=10)

            if resp is not None:
                try:
                    parsed = resp.json()
                    formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
                    response_area.value = f"Статус: {resp.status_code}\n\n{formatted}"
                except:
                    response_area.value = f"Статус: {resp.status_code}\n\n{resp.text[:1000]}"
            else:
                response_area.value = "Неизвестный метод"
        except Exception as ex:
            response_area.value = f"Ошибка запроса: {ex}"

        page.update()

    # ---- Сборка интерфейса ----
    page.add(
        ft.Text("URL и метод", weight=ft.FontWeight.BOLD),
        ft.Row([base_url_field, api_key_value]),
        ft.Row([endpoint_field, method_dropdown]),
       # ft.Row([api_key_name, api_key_value]),
        ft.Divider(),
        ft.Text("Данные запроса", weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.ElevatedButton("Выбрать файл с данными", on_click=pick_file_dialog),
            selected_file_label,
        ]),
        ft.Divider(),
        
        ft.ElevatedButton("Отправить запрос", on_click=send_request),
        response_area,
    )

ft.app(target=main)