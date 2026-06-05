import flet as ft
import requests
import os
import json
import webbrowser
import subprocess
import platform
import time
from tkinter import Tk, filedialog
from datetime import datetime, timedelta

running_tests = False   # глобальный флаг

# Утилита для преобразования JSON в плоские поля (owner[name] и т.д.)
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

def open_file(filepath):
    """Открыть файл в программе по умолчанию"""
    try:
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':
            subprocess.call(('open', filepath))
        else:
            subprocess.call(('xdg-open', filepath))
    except Exception as ex:
        print(f"Не удалось открыть файл {filepath}: {ex}")

def main(page: ft.Page):
    page.title = "API Tester"
    page.window_width = 800
    page.window_height = 700

    # ──────────────────────────────────────────────
    # Контейнеры для трёх режимов
    # ──────────────────────────────────────────────
    manual_container = ft.Column()
    auto_container = ft.Column()
    settings_container = ft.Column()

    # ──────────────────────────────────────────────
    # Кнопки переключения режимов
    # ──────────────────────────────────────────────
    manual_btn = ft.ElevatedButton("Ручной запрос", on_click=lambda e: switch_mode(0))
    auto_btn = ft.ElevatedButton("Автотесты", on_click=lambda e: switch_mode(1))
    settings_btn = ft.ElevatedButton("Настройки", on_click=lambda e: switch_mode(2))

    def switch_mode(index):
        manual_container.visible = (index == 0)
        auto_container.visible = (index == 1)
        settings_container.visible = (index == 2)
        manual_btn.disabled = (index == 0)
        auto_btn.disabled = (index == 1)
        settings_btn.disabled = (index == 2)
        page.update()

    # ──────────────────────────────────────────────
    # РУЧНОЙ РЕЖИМ (с автодатами)
    # ──────────────────────────────────────────────
    base_url_field = ft.TextField(label="Базовый URL", width=420,
                                  value="https://api-eosago.renins.com")
    endpoint_field = ft.TextField(label="Путь (endpoint)", width=420,
                                  value="/calculate/")
    method_dropdown = ft.Dropdown(
        label="Метод", width=100, value="POST",
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
        selected_file_label.value = file_path if file_path else "Файл не выбран"
        page.update()

    api_key_name = ft.TextField(label="Имя параметра (key)", width=200, value="key")
    api_key_value = ft.TextField(label="Значение ключа", width=300, password=True,
                                 value="SECRET_KEY_DEMO")

    response_area = ft.TextField(
        label="Ответ сервера", multiline=True,
        min_lines=6, max_lines=12, read_only=True, width=500,
    )

    def send_request(e):
        base = base_url_field.value.strip().rstrip("/")
        endpoint = endpoint_field.value.strip()
        if not base:
            response_area.value = "Введите базовый URL"
            page.update()
            return

        url = f"{base}/{endpoint.lstrip('/')}" if endpoint else base
        headers = {}
        file_path = selected_file_label.value
        form_data = {}

        if file_path and file_path != "Файл не выбран" and os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                json_obj = json.loads(content)

                # ── Автозаполнение дат ──
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                if "dateStart" in json_obj:
                    json_obj["dateStart"] = tomorrow
                if "usagePeriod" in json_obj and isinstance(json_obj["usagePeriod"], list) and len(json_obj["usagePeriod"]) == 1:
                    period = json_obj["usagePeriod"][0]
                    period["dateStart"] = tomorrow
                    dt_tomorrow = datetime.strptime(tomorrow, "%Y-%m-%d")
                    dt_end = dt_tomorrow.replace(year=dt_tomorrow.year + 1) - timedelta(days=1)
                    period["dateEnd"] = dt_end.strftime("%Y-%m-%d")
                # ─────────────────────────

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

    manual_container.controls = [
        ft.Text("URL и метод", weight=ft.FontWeight.BOLD),
        base_url_field,
        ft.Row([endpoint_field, method_dropdown]),
        ft.Divider(),
        ft.Text("Данные запроса", weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.ElevatedButton("Выбрать файл с данными", on_click=pick_file_dialog),
            selected_file_label,
        ]),
        ft.Divider(),
        ft.Text("Авторизация (API Key в Query)", weight=ft.FontWeight.BOLD),
        ft.Row([api_key_name, api_key_value]),
        ft.Divider(),
        ft.ElevatedButton("Отправить запрос", on_click=send_request),
        response_area,
    ]

    # ──────────────────────────────────────────────
    # АВТОТЕСТЫ (надёжное обновление через контент ячеек)
    # ──────────────────────────────────────────────
    tests_data = []

    # Ширины колонок
    col_widths = [30, 130, 90, 150, 110, 150, 110, 250, 280, 130]

    def open_file_local(filepath):
        """Открыть файл локально (версия внутри main)"""
        try:
            if platform.system() == 'Windows':
                os.startfile(filepath)
            elif platform.system() == 'Darwin':
                subprocess.call(('open', filepath))
            else:
                subprocess.call(('xdg-open', filepath))
        except Exception as ex:
            print(f"Не удалось открыть файл {filepath}: {ex}")

    def make_header(text, width):
        return ft.Container(
            width=width,
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Text(text, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(make_header("№", col_widths[0])),
            ft.DataColumn(make_header("Наименование теста", col_widths[1])),
            ft.DataColumn(make_header("Текущий статус", col_widths[2])),
            ft.DataColumn(make_header("Первый файл", col_widths[3])),
            ft.DataColumn(make_header("ID калькуляции", col_widths[4])),
            ft.DataColumn(make_header("Второй файл", col_widths[5])),
            ft.DataColumn(make_header("ID расчёта", col_widths[6])),
            ft.DataColumn(make_header("Ссылка на оплату", col_widths[7])),
            ft.DataColumn(make_header("Текст ошибки", col_widths[8])),
            ft.DataColumn(make_header("Печатная форма", col_widths[9])),
        ],
        rows=[],
        column_spacing=0,
    )

    # Вспомогательные функции создания неизменяемых частей ячеек
    def make_cell_text(text, width, center=False):
        """Возвращает ft.Text для использования внутри ячейки"""
        return ft.Text(
            text,
            overflow=ft.TextOverflow.ELLIPSIS,
            no_wrap=True,
            text_align=ft.TextAlign.CENTER if center else None,
        )

    def make_cell_container(content, width, tooltip_text=None, center=False):
        """Возвращает ft.Container с заданным содержимым"""
        tooltip = ft.Tooltip(message=tooltip_text, bgcolor="#757575") if tooltip_text else None
        return ft.Container(
            width=width,
            tooltip=tooltip,
            alignment=ft.alignment.Alignment(0, 0) if center else None,
            content=content,
        )

    # Ячейки, которые будут обновляться: статус, calc_id, ras_id, payment_url, error_text
    # Создаются один раз и сохраняются в tests_data

    def select_folder_and_fill(e):
        global running_tests
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory()
        root.destroy()
        if not folder:
            return

        files = os.listdir(folder)
        test_dict = {}

        for fname in files:
            if not os.path.isfile(os.path.join(folder, fname)):
                continue
            if "_Калькуляция_" in fname:
                typ = "Калькуляция"
                parts = fname.split("_Калькуляция_", 1)
            elif "_Расчет_" in fname:
                typ = "Расчет"
                parts = fname.split("_Расчет_", 1)
            else:
                continue

            test_name = parts[0]
            comment = parts[1] if len(parts) > 1 else ""

            if test_name not in test_dict:
                test_dict[test_name] = {}
            if typ == "Калькуляция":
                test_dict[test_name]['calc'] = fname
                test_dict[test_name]['calc_fullpath'] = os.path.join(folder, fname)
            else:
                test_dict[test_name]['ras'] = fname
                test_dict[test_name]['ras_fullpath'] = os.path.join(folder, fname)

        tests_data.clear()
        table.rows.clear()
        for i, (test_name, files_data) in enumerate(test_dict.items(), start=1):
            # Объекты, которые будем обновлять
            status_text = make_cell_text("Ожидание", col_widths[2])
            calc_id_text = make_cell_text("", col_widths[4], center=True)
            ras_id_text = make_cell_text("", col_widths[6], center=True)
            payment_text = make_cell_text("", col_widths[7])
            error_text = make_cell_text("", col_widths[8])

            # Сохраняем в entry для последующего обновления
            entry = {
                "num": i,
                "name": test_name,
                "status": "Ожидание",
                "calc_file": files_data.get('calc', ''),
                "calc_fullpath": files_data.get('calc_fullpath', ''),
                "calc_id": "",
                "ras_file": files_data.get('ras', ''),
                "ras_fullpath": files_data.get('ras_fullpath', ''),
                "ras_id": "",
                "payment_url": "",
                "error_text": "",
                # ссылки на текстовые контролы для обновления
                "status_ctrl": status_text,
                "calc_id_ctrl": calc_id_text,
                "ras_id_ctrl": ras_id_text,
                "payment_ctrl": payment_text,
                "error_ctrl": error_text,
            }
            tests_data.append(entry)

            # Собираем ячейки
            row = ft.DataRow(
                cells=[
                    ft.DataCell(make_cell_container(ft.Text(str(i)), col_widths[0])),
                    ft.DataCell(make_cell_container(ft.Text(test_name), col_widths[1])),
                    ft.DataCell(make_cell_container(status_text, col_widths[2])),
                    ft.DataCell(
                        ft.Container(
                            width=col_widths[3],
                            tooltip=ft.Tooltip(message=entry["calc_fullpath"], bgcolor="#757575"),
                            content=ft.GestureDetector(
                                content=ft.Text(entry["calc_file"], overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                                on_double_tap=lambda e, p=entry["calc_fullpath"]: open_file_local(p) if p else None,
                            ),
                        )
                    ),
                    ft.DataCell(make_cell_container(calc_id_text, col_widths[4], center=True)),
                    ft.DataCell(
                        ft.Container(
                            width=col_widths[5],
                            tooltip=ft.Tooltip(message=entry["ras_fullpath"], bgcolor="#757575"),
                            content=ft.GestureDetector(
                                content=ft.Text(entry["ras_file"], overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                                on_double_tap=lambda e, p=entry["ras_fullpath"]: open_file_local(p) if p else None,
                            ),
                        )
                    ),
                    ft.DataCell(make_cell_container(ras_id_text, col_widths[6], center=True)),
                    ft.DataCell(
                        ft.Container(
                            width=col_widths[7],
                            on_click=lambda e, url=entry["payment_url"]: webbrowser.open(url) if url else None,
                            content=payment_text,
                        )
                    ),
                    ft.DataCell(make_cell_container(error_text, col_widths[8])),
                    ft.DataCell(
                        ft.Container(
                            width=col_widths[9],
                            alignment=ft.alignment.Alignment(0, 0),
                            content=ft.ElevatedButton(
                                "Запросить",
                                on_click=lambda e, idx=i-1: print(f"Запрос для строки {idx}"),
                                width=120,
                                height=40,
                            ),
                        )
                    ),
                ]
            )
            table.rows.append(row)

        running_tests = False
        enable_run_button()
        page.update()

    # Функция обновления текстовых полей (будет вызываться из worker)
    def update_cells(test):
        """Обновляет текстовые поля в ячейках на основе данных test"""
        test["status_ctrl"].value = test["status"]
        test["calc_id_ctrl"].value = test["calc_id"]
        test["ras_id_ctrl"].value = test["ras_id"]
        # Обновление ссылки (меняем url и текст)
        # payment_url может быть ссылкой, мы обновим текст и on_click
        test["payment_ctrl"].value = test["payment_url"]
        # Обновляем обработчик клика для ячейки с оплатой – проще заново не пересоздавать,
        # а обновить on_click у контейнера. Но т.к. контейнер уже создан, можно просто менять url,
        # обернув в замыкание. Мы сохраним контейнер payment в test, чтобы обновить его.
        if "payment_container" in test:
            # Обновим on_click с новым url
            test["payment_container"].on_click = lambda e, url=test["payment_url"]: webbrowser.open(url) if url else None
        test["error_ctrl"].value = test["error_text"]

    # Модифицируем select_folder_and_fill для сохранения контейнера оплаты и обновления
    # Добавим в entry ссылку на контейнер оплаты
    # (перепишем строку с оплатой, чтобы сохранить контейнер)

    # Чтобы не усложнять, заменим select_folder_and_fill на версию, которая сохраняет контейнер оплаты
    # Ниже приведена уже обновлённая версия select_folder_and_fill, которую мы вставим вместо предыдущей.
    # Скопируем её заново с сохранением payment_container.
    # (Для краткости я приведу новый select_folder_and_fill полностью)

    # ================== ЗАМЕНА select_folder_and_fill ==================
    def select_folder_and_fill(e):
        global running_tests
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory()
        root.destroy()
        if not folder:
            return

        files = os.listdir(folder)
        test_dict = {}

        for fname in files:
            if not os.path.isfile(os.path.join(folder, fname)):
                continue
            if "_Калькуляция_" in fname:
                typ = "Калькуляция"
                parts = fname.split("_Калькуляция_", 1)
            elif "_Расчет_" in fname:
                typ = "Расчет"
                parts = fname.split("_Расчет_", 1)
            else:
                continue

            test_name = parts[0]
            comment = parts[1] if len(parts) > 1 else ""

            if test_name not in test_dict:
                test_dict[test_name] = {}
            if typ == "Калькуляция":
                test_dict[test_name]['calc'] = fname
                test_dict[test_name]['calc_fullpath'] = os.path.join(folder, fname)
            else:
                test_dict[test_name]['ras'] = fname
                test_dict[test_name]['ras_fullpath'] = os.path.join(folder, fname)

        tests_data.clear()
        table.rows.clear()
        for i, (test_name, files_data) in enumerate(test_dict.items(), start=1):
            status_text = make_cell_text("Ожидание", col_widths[2])
            calc_id_text = make_cell_text("", col_widths[4], center=True)
            ras_id_text = make_cell_text("", col_widths[6], center=True)
            payment_text = make_cell_text("", col_widths[7])
            error_text = ft.Text( "", overflow=ft.TextOverflow.VISIBLE, no_wrap=False,)

            # Контейнер оплаты с ссылкой
            payment_container = ft.Container(
                width=col_widths[7],
                on_click=None,
                content=payment_text,
            )
            # Если есть url, сделаем позже

            entry = {
                "num": i,
                "name": test_name,
                "status": "Ожидание",
                "calc_file": files_data.get('calc', ''),
                "calc_fullpath": files_data.get('calc_fullpath', ''),
                "calc_id": "",
                "ras_file": files_data.get('ras', ''),
                "ras_fullpath": files_data.get('ras_fullpath', ''),
                "ras_id": "",
                "payment_url": "",
                "error_text": "",
                "status_ctrl": status_text,
                "calc_id_ctrl": calc_id_text,
                "ras_id_ctrl": ras_id_text,
                "payment_ctrl": payment_text,
                "error_ctrl": error_text,
                "payment_container": payment_container,   # сохраняем контейнер для обновления on_click
            }
            tests_data.append(entry)

            row = ft.DataRow(
                cells=[
                    ft.DataCell(make_cell_container(ft.Text(str(i)), col_widths[0])),
                    ft.DataCell(make_cell_container(ft.Text(test_name), col_widths[1])),
                    ft.DataCell(make_cell_container(status_text, col_widths[2])),
                    ft.DataCell(
                        ft.Container(
                            width=col_widths[3],
                            tooltip=ft.Tooltip(message=entry["calc_fullpath"], bgcolor="#757575"),
                            content=ft.GestureDetector(
                                content=ft.Text(entry["calc_file"], overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                                on_double_tap=lambda e, p=entry["calc_fullpath"]: open_file_local(p) if p else None,
                            ),
                        )
                    ),
                    ft.DataCell(make_cell_container(calc_id_text, col_widths[4], center=True)),
                    ft.DataCell(
                        ft.Container(
                            width=col_widths[5],
                            tooltip=ft.Tooltip(message=entry["ras_fullpath"], bgcolor="#757575"),
                            content=ft.GestureDetector(
                                content=ft.Text(entry["ras_file"], overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                                on_double_tap=lambda e, p=entry["ras_fullpath"]: open_file_local(p) if p else None,
                            ),
                        )
                    ),
                    ft.DataCell(make_cell_container(ras_id_text, col_widths[6], center=True)),
                    ft.DataCell(payment_container),
                    ft.DataCell(make_cell_container(error_text, col_widths[8])),
                    ft.DataCell(
                        ft.Container(
                            width=col_widths[9],
                            alignment=ft.alignment.Alignment(0, 0),
                            content=ft.ElevatedButton(
                                "Запросить",
                                on_click=lambda e, idx=i-1: print(f"Запрос для строки {idx}"),
                                width=120,
                                height=40,
                            ),
                        )
                    ),
                ]
            )
            table.rows.append(row)

        running_tests = False
        enable_run_button()
        page.update()

    # ──────────────────────────────────────────────
    # ФУНКЦИЯ ЗАПУСКА ВСЕХ ТЕСТОВ
    # ──────────────────────────────────────────────
    # ──────────────────────────────────────────────
    # ФУНКЦИЯ ЗАПУСКА ВСЕХ ТЕСТОВ (с page.run_thread)
    # ──────────────────────────────────────────────
    def run_all_tests(e):
        global running_tests
        if running_tests:
            return
        running_tests = True
        run_all_tests_btn.disabled = True
        activate_all_btn.disabled = True
        page.update()

        def worker():
            base_url = base_url_field.value.strip().rstrip("/")
            key_value = api_key_value.value

            # Читаем настройки повторов (с проверкой)
            try:
                max_retries = int(retry_count_field.value)
            except:
                max_retries = 5
            try:
                retry_delay = float(retry_delay_field.value)
            except:
                retry_delay = 3.0

            for i, test in enumerate(tests_data):
                # ── Этап 1: Калькуляция ──────────────────────────────
                test["status"] = "Выполняется расчёт"
                test["error_text"] = ""
                test["calc_id"] = ""
                test["ras_id"] = ""
                update_cells(test)
                page.update()

                calc_path = test.get("calc_fullpath", "")
                if not calc_path or not os.path.isfile(calc_path):
                    test["status"] = "Ошибка"
                    test["error_text"] = "Файл калькуляции не найден"
                    update_cells(test)
                    page.update()
                    continue

                try:
                    with open(calc_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    json_obj = json.loads(content)

                    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                    if "dateStart" in json_obj:
                        json_obj["dateStart"] = tomorrow
                    if "usagePeriod" in json_obj and isinstance(json_obj["usagePeriod"], list) and len(json_obj["usagePeriod"]) == 1:
                        period = json_obj["usagePeriod"][0]
                        period["dateStart"] = tomorrow
                        dt_tomorrow = datetime.strptime(tomorrow, "%Y-%m-%d")
                        dt_end = dt_tomorrow.replace(year=dt_tomorrow.year + 1) - timedelta(days=1)
                        period["dateEnd"] = dt_end.strftime("%Y-%m-%d")

                    form_data = flatten_json(json_obj)
                    form_data["key"] = key_value

                    endpoint = method_endpoint_fields["Создание заявки на расчёт"].value.strip()
                    url = f"{base_url}/{endpoint.lstrip('/')}" if endpoint else base_url
                    resp = requests.post(url, data=form_data, timeout=10)

                    if resp.status_code == 200:
                        try:
                            parsed = resp.json()
                            data_val = parsed.get("data", [])
                            msg = parsed.get("message", "")
                            if isinstance(data_val, list) and len(data_val) > 0:
                                test["calc_id"] = str(data_val[0])
                            else:
                                test["calc_id"] = ""

                            if not parsed.get("result", True):
                                test["status"] = "Ошибка"
                                test["error_text"] = msg
                                update_cells(test)
                                page.update()
                                continue
                            else:
                                test["status"] = "Расчёт получен"
                        except Exception:
                            test["status"] = "Ошибка"
                            test["error_text"] = "Неверный JSON ответ"
                            update_cells(test)
                            page.update()
                            continue
                    else:
                        test["status"] = "Ошибка"
                        test["error_text"] = f"HTTP {resp.status_code} : {resp.text[:200]}"
                        update_cells(test)
                        page.update()
                        continue

                    update_cells(test)
                    page.update()

                except Exception as ex:
                    test["status"] = "Ошибка"
                    test["error_text"] = str(ex)
                    update_cells(test)
                    page.update()
                    continue

                # ── Этап 2: Создание договора (с повторными попытками) ──
                test["status"] = "Создание договора"
                update_cells(test)
                page.update()

                ras_path = test.get("ras_fullpath", "")
                if not ras_path or not os.path.isfile(ras_path):
                    test["status"] = "Ошибка"
                    test["error_text"] = "Файл расчёта не найден"
                    update_cells(test)
                    page.update()
                    continue

                try:
                    with open(ras_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    json_ras = json.loads(content)

                    json_ras["calculationId"] = test["calc_id"]
                    json_ras["key"] = key_value

                    endpoint2 = method_endpoint_fields["Создание договора"].value.strip()
                    url2 = f"{base_url}/{endpoint2.lstrip('/')}" if endpoint2 else base_url

                    success = False
                    last_error = ""

                    for attempt in range(1, max_retries + 1):
                        resp2 = requests.post(url2, data=json_ras, timeout=10)

                        if resp2.status_code == 200:
                            try:
                                parsed = resp2.json()
                                data_val = parsed.get("data", {})
                                msg = parsed.get("message", "")

                                if isinstance(data_val, dict) and "policyId" in data_val:
                                    test["ras_id"] = str(data_val["policyId"])
                                    test["status"] = "Договор создан"
                                    success = True
                                    break
                                elif "Не найден расчет" in msg:
                                    last_error = msg
                                    if attempt < max_retries:
                                        time.sleep(retry_delay)
                                        continue
                                    else:
                                        test["status"] = "Ошибка"
                                        test["error_text"] = f"Исчерпаны попытки: {msg}"
                                        break
                                else:
                                    test["status"] = "Ошибка"
                                    test["error_text"] = msg
                                    break
                            except Exception:
                                test["status"] = "Ошибка"
                                test["error_text"] = "Неверный JSON ответ (договор)"
                                break
                        else:
                            last_error = f"HTTP {resp2.status_code} : {resp2.text[:200]}"
                            if attempt < max_retries:
                                time.sleep(retry_delay)
                                continue
                            else:
                                test["status"] = "Ошибка"
                                test["error_text"] = f"Исчерпаны попытки: {last_error}"
                                break

                    if not success and test["status"] not in ("Ошибка", "Договор создан"):
                        test["status"] = "Ошибка"
                        if not test["error_text"]:
                            test["error_text"] = last_error or "Неизвестная ошибка"

                except Exception as ex:
                    test["status"] = "Ошибка"
                    test["error_text"] = str(ex)

                update_cells(test)
                page.update()

            run_all_tests_btn.disabled = False
            activate_all_btn.disabled = False
            running_tests = False
            page.update()

        # Запускаем worker через page.run_thread – это гарантирует, что page.update() будет работать
        page.run_thread(worker)

    # Кнопки действий
    run_all_tests_btn = ft.ElevatedButton(
        "Запустить все тесты",
        on_click=run_all_tests,
        disabled=True,
    )

    activate_all_btn = ft.ElevatedButton(
        "Перевести в действующие",
        on_click=lambda e: print("Перевод всех в действующие (заглушка)"),
        disabled=True,
    )

    def enable_run_button():
        has_rows = len(tests_data) > 0
        run_all_tests_btn.disabled = not has_rows
        activate_all_btn.disabled = not has_rows
        page.update()

    # Обёртка для заполнения папки
    def select_folder_and_fill_wrapper(e):
        select_folder_and_fill(e)

    auto_container.controls = [
        ft.Text("Массовое тестирование", weight=ft.FontWeight.BOLD, size=16),
        ft.Row([
            ft.ElevatedButton("Заполнить таблицу из папки", on_click=select_folder_and_fill_wrapper),
            run_all_tests_btn,
            activate_all_btn,
        ]),
        ft.Divider(),
        ft.Text("Результаты тестов:", weight=ft.FontWeight.BOLD),
        ft.Row([table], scroll=ft.ScrollMode.AUTO),
    ]

    # ──────────────────────────────────────────────
    # НАСТРОЙКИ (эндпоинты для семи методов)
    # ──────────────────────────────────────────────
    default_endpoints = {
        "Создание заявки на расчёт": "/calculate/",
        "Создание договора": "/create/",
        "Получение статуса договора": "/contract_status/",
        "Ссылка на форму оплаты": "/payment_link/",
        "Получение ПДФ образца": "/pdf_sample/",
        "Перевод в действующие": "/activate/",
        "Получение ПДФ документа": "/pdf_document/",
    }

    method_endpoint_fields = {}
    settings_rows = []
    for method_name, default_url in default_endpoints.items():
        label = ft.Text(method_name, width=220)
        field = ft.TextField(value=default_url, width=400)
        method_endpoint_fields[method_name] = field
        settings_rows.append(ft.Row([label, field]))

    # Поля для повторов
    retry_count_field = ft.TextField(label="Количество попыток", value="5", width=200)
    retry_delay_field = ft.TextField(label="Пауза между попытками (сек)", value="3", width=200)

    # Добавляем их в тот же список settings_rows
    settings_rows.append(ft.Divider())
    settings_rows.append(ft.Text("Параметры повторов", weight=ft.FontWeight.BOLD))
    settings_rows.append(ft.Row([retry_count_field, retry_delay_field]))

    # Теперь финальное присваивание – всё попадёт на экран
    settings_container.controls = [
        ft.Text("Настройки эндпоинтов", weight=ft.FontWeight.BOLD, size=16),
        ft.Text("Укажите относительные пути (или полные URL) для каждого запроса."),
    ] + settings_rows

    # ──────────────────────────────────────────────
    # Начальное состояние
    # ──────────────────────────────────────────────
    manual_container.visible = True
    auto_container.visible = False
    settings_container.visible = False
    manual_btn.disabled = True
    auto_btn.disabled = False
    settings_btn.disabled = False

    page.add(
        ft.Row([manual_btn, auto_btn, settings_btn]),
        manual_container,
        auto_container,
        settings_container,
    )

ft.app(target=main)