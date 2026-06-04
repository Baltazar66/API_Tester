import flet as ft
import requests
import os
from tkinter import Tk, filedialog

def main(page: ft.Page):
    page.title = "API Tester"
    page.window_width = 500
    page.window_height = 400

    url_field = ft.TextField(label="URL API", width=400, value="https://jsonplaceholder.typicode.com/posts")
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

    response_area = ft.TextField(
        label="Ответ сервера",
        multiline=True,
        min_lines=4,
        max_lines=8,
        read_only=True,
        width=400,
    )

    def send_request(e):
        url = url_field.value.strip()
        method = method_dropdown.value
        if not url:
            response_area.value = "Введите URL"
            page.update()
            return

        file_path = selected_file_label.value
        data = None
        if file_path and file_path != "Файл не выбран" and os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = f.read()
            except Exception as ex:
                response_area.value = f"Ошибка чтения файла: {ex}"
                page.update()
                return

        try:
            if method == "GET":
                resp = requests.get(url, timeout=10)
            elif method == "POST":
                resp = requests.post(url, data=data, timeout=10)
            elif method == "PUT":
                resp = requests.put(url, data=data, timeout=10)
            elif method == "DELETE":
                resp = requests.delete(url, timeout=10)
            else:
                resp = None

            if resp is not None:
                response_area.value = f"Статус: {resp.status_code}\n\n{resp.text[:1000]}"
            else:
                response_area.value = "Неизвестный метод"
        except Exception as ex:
            response_area.value = f"Ошибка запроса: {ex}"

        page.update()

    page.add(
        ft.Row([url_field, method_dropdown]),
        ft.Row([
            ft.ElevatedButton("Выбрать файл с данными", on_click=pick_file_dialog),
            selected_file_label,
        ]),
        ft.ElevatedButton("Отправить запрос", on_click=send_request),
        response_area,
    )

ft.app(target=main)