import flet as ft
import requests
import os
import json
import webbrowser
import subprocess
import platform
import time
import base64
from tkinter import Tk, filedialog
from datetime import datetime, timedelta

running_tests = False

# Утилита для преобразования JSON в плоские поля
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
    page.window_width = 1100
    page.window_height = 700

    manual_container = ft.Column()
    auto_container = ft.Column()
    settings_container = ft.Column()

    manual_btn = ft.Button("Ручной запрос", on_click=lambda e: switch_mode(0))
    auto_btn = ft.Button("Автотесты", on_click=lambda e: switch_mode(1))
    settings_btn = ft.Button("Настройки", on_click=lambda e: switch_mode(2))

    def switch_mode(index):
        manual_container.visible = (index == 0)
        auto_container.visible = (index == 1)
        settings_container.visible = (index == 2)
        manual_btn.disabled = (index == 0)
        auto_btn.disabled = (index == 1)
        settings_btn.disabled = (index == 2)
        page.update()

    base_url_field = ft.TextField(label="Базовый URL", width=420, value="https://api-eosago.renins.com")
    endpoint_field = ft.TextField(label="Путь (endpoint)", width=420, value="/calculate/")
    method_dropdown = ft.Dropdown(label="Метод", width=100, value="POST",
                                  options=[ft.dropdown.Option("GET"), ft.dropdown.Option("POST"),
                                           ft.dropdown.Option("PUT"), ft.dropdown.Option("DELETE")])

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
    api_key_value = ft.TextField(label="Значение ключа", width=300, password=True, value="SECRET_KEY_DEMO")

    response_area = ft.TextField(label="Ответ сервера", multiline=True, min_lines=6, max_lines=12, read_only=True, width=500)

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
        ft.Row([ft.Button("Выбрать файл с данными", on_click=pick_file_dialog), selected_file_label]),
        ft.Divider(),
        ft.Text("Авторизация (API Key в Query)", weight=ft.FontWeight.BOLD),
        ft.Row([api_key_name, api_key_value]),
        ft.Divider(),
        ft.Button("Отправить запрос", on_click=send_request),
        response_area,
    ]

    # ================== АВТОТЕСТЫ ==================
    tests_data = []
    col_widths = [30, 110, 130, 120, 100, 120, 110, 120, 90, 220, 200, 130]

    selected_document_index = -1

    def on_sample_click(e):
        nonlocal selected_document_index
        if selected_document_index >= 0:
            request_document(selected_document_index, 'sample')
        pdf_choice_panel.visible = False
        page.update()

    def on_policy_click(e):
        nonlocal selected_document_index
        if selected_document_index >= 0:
            request_document(selected_document_index, 'policy')
        pdf_choice_panel.visible = False
        page.update()

    pdf_choice_panel = ft.Row(
        [ft.Text("Выберите тип документа: "),
         ft.Button("Образец", on_click=on_sample_click),
         ft.Button("Полис", on_click=on_policy_click)],
        visible=False,
    )

    def open_file_local(filepath):
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
        return ft.Container(width=width, alignment=ft.alignment.Alignment(0, 0),
                            content=ft.Text(text, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER))

    table = ft.DataTable(
        columns=[
            ft.DataColumn(make_header("№", col_widths[0])),
            ft.DataColumn(make_header("Статус тестирования", col_widths[1])),
            ft.DataColumn(make_header("Наименование теста", col_widths[2])),
            ft.DataColumn(make_header("Критерий прохождения", col_widths[3])),
            ft.DataColumn(make_header("Текущий статус", col_widths[4])),
            ft.DataColumn(make_header("Первый файл", col_widths[5])),
            ft.DataColumn(make_header("ID калькуляции", col_widths[6])),
            ft.DataColumn(make_header("Второй файл", col_widths[7])),
            ft.DataColumn(make_header("ID расчёта", col_widths[8])),
            ft.DataColumn(make_header("Ссылка на оплату", col_widths[9])),
            ft.DataColumn(make_header("Текст ошибки", col_widths[10])),
            ft.DataColumn(make_header("Печатная форма", col_widths[11])),
        ],
        rows=[],
        column_spacing=0,
    )

    def make_cell_text(text, width, center=False):
        return ft.Text(text, overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True,
                       text_align=ft.TextAlign.CENTER if center else None)

    def make_cell_container(content, width, tooltip_text=None, center=False):
        tooltip = ft.Tooltip(message=tooltip_text, bgcolor="#757575") if tooltip_text else None
        return ft.Container(width=width, tooltip=tooltip,
                            alignment=ft.alignment.Alignment(0, 0) if center else None,
                            content=content)

    def select_folder_and_fill(e):
        global running_tests
        nonlocal selected_document_index
        selected_document_index = -1
        pdf_choice_panel.visible = False
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
            # Удаляем расширение файла из комментария
            criteria = comment.rsplit('.', 1)[0] if '.' in comment else comment

            if test_name not in test_dict:
                test_dict[test_name] = {}
            if typ == "Калькуляция":
                test_dict[test_name]['calc'] = fname
                test_dict[test_name]['calc_fullpath'] = os.path.join(folder, fname)
                if 'criteria' not in test_dict[test_name] or not test_dict[test_name]['criteria']:
                    test_dict[test_name]['criteria'] = criteria
            else:
                test_dict[test_name]['ras'] = fname
                test_dict[test_name]['ras_fullpath'] = os.path.join(folder, fname)
                if 'criteria' not in test_dict[test_name] or not test_dict[test_name]['criteria']:
                    test_dict[test_name]['criteria'] = criteria

        tests_data.clear()
        table.rows.clear()
        for i, (test_name, files_data) in enumerate(test_dict.items(), start=1):
            criteria = files_data.get('criteria', '')
            status_text = ft.Text("Ожидание", no_wrap=False, overflow=ft.TextOverflow.VISIBLE,
                                  width=col_widths[4], max_lines=3, text_align=ft.TextAlign.CENTER)
            calc_id_text = make_cell_text("", col_widths[6], center=True)
            ras_id_text = make_cell_text("", col_widths[8], center=True)
            payment_text = ft.TextField(value="", read_only=True, multiline=False,
                                        border="none", text_style=ft.TextStyle(size=12), width=col_widths[9])
            error_text = ft.TextField(value="", read_only=True, multiline=True,
                                      min_lines=1, max_lines=3, border="none",
                                      text_style=ft.TextStyle(size=12), width=col_widths[10])
            test_status_ctrl = ft.Text("Не начат", width=col_widths[1], text_align=ft.TextAlign.CENTER, overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True,)
            criteria_ctrl = ft.Text(
                criteria,
                width=col_widths[3],
                text_align=ft.TextAlign.CENTER,
                no_wrap=False,
                max_lines=3,
                overflow=ft.TextOverflow.ELLIPSIS,
            )

            payment_container = ft.Container(width=col_widths[9], on_click=None, content=payment_text)

            entry = {
                "num": i,
                "test_status": "Не начат",
                "name": test_name,
                "criteria": criteria,
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
                "payment_container": payment_container,
                "test_status_ctrl": test_status_ctrl,
                "criteria_ctrl": criteria_ctrl,
            }
            tests_data.append(entry)

            row = ft.DataRow(
                cells=[
                    ft.DataCell(make_cell_container(ft.Text(str(i)), col_widths[0])),
                    ft.DataCell(make_cell_container(test_status_ctrl, col_widths[1], center=True)),
                    ft.DataCell(make_cell_container(make_cell_text(test_name, col_widths[2], center=True), col_widths[2])),
                    ft.DataCell(make_cell_container(criteria_ctrl, col_widths[3])),
                    ft.DataCell(ft.Container(width=col_widths[4], content=status_text)),
                    ft.DataCell(ft.Container(width=col_widths[5],
                                             tooltip=ft.Tooltip(message=entry["calc_fullpath"], bgcolor="#757575"),
                                             content=ft.GestureDetector(
                                                 content=ft.Text(entry["calc_file"], overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                                                 on_double_tap=lambda e, p=entry["calc_fullpath"]: open_file_local(p) if p else None))),
                    ft.DataCell(make_cell_container(calc_id_text, col_widths[6], center=True)),
                    ft.DataCell(ft.Container(width=col_widths[7],
                                             tooltip=ft.Tooltip(message=entry["ras_fullpath"], bgcolor="#757575"),
                                             content=ft.GestureDetector(
                                                 content=ft.Text(entry["ras_file"], overflow=ft.TextOverflow.ELLIPSIS, no_wrap=True),
                                                 on_double_tap=lambda e, p=entry["ras_fullpath"]: open_file_local(p) if p else None))),
                    ft.DataCell(make_cell_container(ras_id_text, col_widths[8], center=True)),
                    ft.DataCell(payment_container),
                    ft.DataCell(make_cell_container(error_text, col_widths[10])),
                    ft.DataCell(ft.Container(width=col_widths[11], alignment=ft.alignment.Alignment(0, 0),
                                             content=ft.Button("Запросить", on_click=lambda e, idx=i-1: on_request_button_click(idx),
                                                               width=120, height=45))),
                ]
            )
            table.rows.append(row)

        running_tests = False
        enable_run_button()
        update_activate_button_state()
        page.update()

    def update_cells(test):
        test["status_ctrl"].value = test["status"]
        if test["status"] in ("Готов", "Согласован", "Оформлен"):
            test["status_ctrl"].color = ft.Colors.GREEN
        elif test["status"] in ("Ошибка калькуляции", "Ошибка расчета", "Ошибка активации"):
            test["status_ctrl"].color = ft.Colors.YELLOW
        elif test["status"] == "Ошибка":
            test["status_ctrl"].color = ft.Colors.RED
        else:
            test["status_ctrl"].color = None
        test["calc_id_ctrl"].value = test["calc_id"]
        test["ras_id_ctrl"].value = test["ras_id"]
        test["payment_ctrl"].value = test["payment_url"]
        if "payment_container" in test and test["payment_url"]:
            test["payment_container"].on_click = lambda e, url=test["payment_url"]: webbrowser.open(url) if url else None
        else:
            if "payment_container" in test:
                test["payment_container"].on_click = None
        test["error_ctrl"].value = test["error_text"]
        test["test_status_ctrl"].value = test.get("test_status", "Не начат")
        test["criteria_ctrl"].value = test.get("criteria", "")
        update_activate_button_state()

    def compute_final_test_status(test):
        status = test["status"]
        criteria = test.get("criteria", "")
        # Если критерий точно совпадает с текущим статусом (включая любые ошибки)
        if criteria and criteria == status:
            test["test_status"] = "Пройден"
        # Особая логика: если критерий "Согласовано", а статус "Оформлен" – тоже Пройден
        elif status == "Оформлен" and criteria == "Согласовано":
            test["test_status"] = "Пройден"
        # В остальных случаях – Не пройден
        else:
            test["test_status"] = "Не пройден"

        # Обновляем контрол и цвет
        test["test_status_ctrl"].value = test["test_status"]
        if test["test_status"] == "Пройден":
            test["test_status_ctrl"].color = ft.Colors.GREEN
        elif test["test_status"] == "Не пройден":
            test["test_status_ctrl"].color = ft.Colors.RED
        else:
            test["test_status_ctrl"].color = None

    def fetch_and_save_pdf(url, prefix, policy_id):
        try:
            timeout = float(timeout_field.value) if timeout_field.value else 30.0
            resp = requests.get(url, timeout=timeout)
            if resp.status_code != 200:
                print(f"Ошибка запроса PDF: {resp.status_code}")
                return
            data = resp.json()
            b64 = data.get("return") or data.get("data", {}).get("return")
            if not b64:
                if isinstance(data.get("data"), str):
                    b64 = data["data"]
            if not b64:
                print("Не удалось найти base64 строку в ответе")
                return
            pdf_bytes = base64.b64decode(b64)
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")],
                                                     initialfile=f"{prefix}_{policy_id}.pdf")
            root.destroy()
            if file_path:
                with open(file_path, 'wb') as f:
                    f.write(pdf_bytes)
                print(f"Файл сохранён: {file_path}")
        except Exception as ex:
            print(f"Ошибка при получении/сохранении PDF: {ex}")

    def on_request_button_click(index):
        if index < 0 or index >= len(tests_data):
            return
        test = tests_data[index]
        policy_id = test.get("ras_id", "")
        if not policy_id:
            return
        status = test["status"]
        if status == "Согласован":
            request_document(index, 'sample')
        elif status in ("Готов", "Оформлен"):
            nonlocal selected_document_index
            selected_document_index = index
            pdf_choice_panel.visible = True
            page.update()

    def request_document(index, doc_type):
        test = tests_data[index]
        policy_id = test.get("ras_id", "")
        if not policy_id:
            return
        key_value = api_key_value.value
        base_url = base_url_field.value.strip().rstrip("/")
        if doc_type == 'sample':
            endpoint_template = method_endpoint_fields["Получение ПДФ образца"].value.strip()
            prefix = "образец"
        else:
            endpoint_template = method_endpoint_fields["Получение ПДФ документа"].value.strip()
            prefix = "полис"
        path = endpoint_template.replace("{policyId}", policy_id)
        url = f"{base_url}/{path.lstrip('/')}?key={key_value}"
        fetch_and_save_pdf(url, prefix, policy_id)

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
            try: max_retries = int(retry_count_field.value)
            except: max_retries = 5
            try: retry_delay = float(retry_delay_field.value)
            except: retry_delay = 3.0
            try: request_timeout = float(timeout_field.value)
            except: request_timeout = 30.0
            try: poll_interval = float(status_poll_interval_field.value)
            except: poll_interval = 10.0

            for i, test in enumerate(tests_data):
                test["test_status"] = "Выполняется"
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
                    test["test_status"] = "Не пройден"
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
                    resp = requests.post(url, data=form_data, timeout=request_timeout)
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
                                test["test_status"] = "Не пройден"
                                update_cells(test)
                                page.update()
                                continue
                            else:
                                test["status"] = "Расчёт получен"
                        except Exception:
                            test["status"] = "Ошибка"
                            test["error_text"] = "Неверный JSON ответ"
                            test["test_status"] = "Не пройден"
                            update_cells(test)
                            page.update()
                            continue
                    else:
                        test["status"] = "Ошибка"
                        test["error_text"] = f"HTTP {resp.status_code} : {resp.text[:200]}"
                        test["test_status"] = "Не пройден"
                        update_cells(test)
                        page.update()
                        continue
                    update_cells(test)
                    page.update()
                except Exception as ex:
                    test["status"] = "Ошибка"
                    test["error_text"] = str(ex)
                    test["test_status"] = "Не пройден"
                    update_cells(test)
                    page.update()
                    continue

                # Проверка статуса калькуляции
                test["status"] = "Проверка статуса"
                update_cells(test)
                page.update()
                calc_template = method_endpoint_fields["Получение статуса калькуляции"].value.strip()
                calc_url_path = calc_template.replace("{id}", test["calc_id"])
                calc_status_url = f"{base_url}/{calc_url_path.lstrip('/')}?key={key_value}"
                calc_status_ok = False
                calc_final_error = ""
                for calc_attempt in range(1, max_retries + 1):
                    try:
                        resp_calc_status = requests.get(calc_status_url, timeout=request_timeout)
                        if resp_calc_status.status_code == 200:
                            calc_status = resp_calc_status.json()
                            if calc_status.get("result") == True:
                                calc_status_ok = True
                                break
                            else:
                                msg = calc_status.get("data", "")
                                if isinstance(msg, str) and "Расчет не окончен (A)" in msg:
                                    if calc_attempt < max_retries:
                                        time.sleep(retry_delay)
                                        continue
                                    else:
                                        calc_final_error = f"Исчерпаны попытки: {msg}"
                                        break
                                else:
                                    calc_final_error = msg if isinstance(msg, str) else json.dumps(msg, ensure_ascii=False)
                                    break
                        else:
                            if calc_attempt < max_retries:
                                time.sleep(retry_delay)
                                continue
                            else:
                                calc_final_error = f"HTTP {resp_calc_status.status_code} : {resp_calc_status.text[:200]}"
                                break
                    except Exception as ex:
                        if calc_attempt < max_retries:
                            time.sleep(retry_delay)
                            continue
                        else:
                            calc_final_error = f"Ошибка запроса: {str(ex)}"
                            break
                if not calc_status_ok:
                    # Если ошибка именно из-за "Расчет не окончен (A)" – это техническая ошибка
                    if calc_final_error and "Расчет не окончен (A)" in calc_final_error:
                        test["status"] = "Ошибка"
                    else:
                        test["status"] = "Ошибка калькуляции"
                    test["error_text"] = calc_final_error if calc_final_error else "Не удалось проверить статус калькуляции"
                    test["test_status"] = "Не пройден"
                    update_cells(test)
                    page.update()
                    continue

                # Создание договора
                test["status"] = "Создание договора"
                update_cells(test)
                page.update()
                ras_path = test.get("ras_fullpath", "")
                if not ras_path or not os.path.isfile(ras_path):
                    test["status"] = "Ошибка"
                    test["error_text"] = "Файл расчёта не найден"
                    test["test_status"] = "Не пройден"
                    update_cells(test)
                    page.update()
                    continue
                try:
                    with open(ras_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    json_ras = json.loads(content)
                    form_data_ras = flatten_json(json_ras)
                    form_data_ras["calculationId"] = test["calc_id"]
                    form_data_ras["key"] = key_value
                    endpoint2 = method_endpoint_fields["Создание договора"].value.strip()
                    url2 = f"{base_url}/{endpoint2.lstrip('/')}" if endpoint2 else base_url
                    success = False
                    last_error = ""
                    for attempt in range(1, max_retries + 1):
                        resp2 = requests.post(url2, data=form_data_ras, timeout=request_timeout)
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
                                        test["test_status"] = "Не пройден"
                                        break
                                else:
                                    test["status"] = "Ошибка"
                                    test["error_text"] = msg
                                    test["test_status"] = "Не пройден"
                                    break
                            except Exception:
                                test["status"] = "Ошибка"
                                test["error_text"] = "Неверный JSON ответ (договор)"
                                test["test_status"] = "Не пройден"
                                break
                        else:
                            last_error = f"HTTP {resp2.status_code} : {resp2.text[:200]}"
                            if attempt < max_retries:
                                time.sleep(retry_delay)
                                continue
                            else:
                                test["status"] = "Ошибка"
                                test["error_text"] = f"Исчерпаны попытки: {last_error}"
                                test["test_status"] = "Не пройден"
                                break
                    if not success and test["status"] not in ("Ошибка", "Договор создан"):
                        test["status"] = "Ошибка"
                        if not test["error_text"]:
                            test["error_text"] = last_error or "Неизвестная ошибка"
                        test["test_status"] = "Не пройден"
                except Exception as ex:
                    test["status"] = "Ошибка"
                    test["error_text"] = str(ex)
                    test["test_status"] = "Не пройден"
                update_cells(test)
                page.update()

            # Опрос статуса договора
            while True:
                any_pending = False
                for test in tests_data:
                    if test["ras_id"] and test["status"] not in ("Ошибка", "Готов", "Согласован", "Ошибка расчета", "Ошибка калькуляции", "Ошибка активации"):
                        any_pending = True
                        endpoint_template = method_endpoint_fields["Получение статуса договора"].value.strip()
                        path = endpoint_template.replace("{policyId}", test["ras_id"])
                        status_url = f"{base_url}/{path.lstrip('/')}?key={key_value}"
                        try:
                            resp = requests.get(status_url, timeout=request_timeout)
                            if resp.status_code == 200:
                                data = resp.json()
                                result = data.get("result")
                                if result == True:
                                    status_val = None
                                    data_content = data.get("data")
                                    if isinstance(data_content, dict):
                                        status_val = data_content.get("Status")
                                    elif isinstance(data_content, list) and len(data_content) > 0:
                                        first = data_content[0]
                                        if isinstance(first, dict):
                                            status_val = first.get("Status")
                                        elif isinstance(first, str):
                                            pass
                                    if status_val and str(status_val).strip().lower() == "ok":
                                        test["status"] = "Согласован"
                                    else:
                                        test["status"] = "Готов"
                                elif result == False:
                                    msg = data.get("message", "")
                                    if "Ожидание проверки в РСА" in msg:
                                        test["status"] = "Проверка РСА"
                                    else:
                                        test["status"] = "Ошибка расчета"
                                        test["error_text"] = msg
                        except Exception:
                            pass
                        update_cells(test)
                        page.update()
                if not any_pending:
                    break
                time.sleep(poll_interval)

            # Вычисляем финальный статус тестирования для всех строк
            for test in tests_data:
                compute_final_test_status(test)
                update_cells(test)
                page.update()

            update_activate_button_state()

            # Запрос ссылки на оплату
            endpoint_template_payment = method_endpoint_fields["Ссылка на форму оплаты"].value.strip()
            for test in tests_data:
                if test["status"] == "Согласован" and test["ras_id"]:
                    path = endpoint_template_payment.replace("{policyId}", test["ras_id"])
                    payment_url = f"{base_url}/{path.lstrip('/')}"
                    post_data = {"key": key_value, "fail_url": fail_url_field.value, "success_url": success_url_field.value}
                    try:
                        resp = requests.post(payment_url, data=post_data, timeout=request_timeout)
                        if resp.status_code == 200:
                            data = resp.json()
                            url_value = ""
                            data_obj = data.get("data")
                            if isinstance(data_obj, dict):
                                url_value = data_obj.get("url", "")
                            elif isinstance(data_obj, list) and len(data_obj) > 0:
                                first = data_obj[0]
                                if isinstance(first, dict):
                                    url_value = first.get("url", "")
                                elif isinstance(first, str):
                                    url_value = first
                            elif isinstance(data_obj, str):
                                url_value = data_obj
                            if url_value:
                                test["payment_url"] = url_value
                            else:
                                test["payment_url"] = "Ссылка не получена"
                        else:
                            test["payment_url"] = f"Ошибка HTTP {resp.status_code}"
                    except Exception as ex:
                        test["payment_url"] = f"Ошибка: {str(ex)}"
                    update_cells(test)
                    page.update()

            update_activate_button_state()
            run_all_tests_btn.disabled = False
            activate_all_btn.disabled = False
            running_tests = False
            page.update()

        page.run_thread(worker)

    run_all_tests_btn = ft.Button("Запустить все тесты", on_click=run_all_tests, disabled=True)

    def activate_all(e):
        base_url = base_url_field.value.strip().rstrip("/")
        key_value = api_key_value.value
        endpoint_template = method_endpoint_fields["Перевод в действующие"].value.strip()
        timeout = float(timeout_field.value) if timeout_field.value else 30.0
        for test in tests_data:
            if test["status"] == "Согласован" and test["ras_id"]:
                path = endpoint_template.replace("{policyId}", test["ras_id"])
                url = f"{base_url}/{path.lstrip('/')}?key={key_value}"
                try:
                    resp = requests.get(url, timeout=timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        if (data.get("result") == True and isinstance(data.get("data"), dict) and
                            data["data"].get("result") == True and isinstance(data["data"].get("return"), dict) and
                            data["data"]["return"].get("Status") == True and data.get("message") == "ok"):
                            test["status"] = "Оформлен"
                        else:
                            error_msg = (data.get("message") or
                                         (data.get("data", {}).get("message") if isinstance(data.get("data"), dict) else None) or
                                         "Не удалось активировать")
                            test["status"] = "Ошибка активации"
                            test["error_text"] = error_msg
                    else:
                        test["status"] = "Ошибка активации"
                        test["error_text"] = f"HTTP {resp.status_code}"
                except Exception as ex:
                    test["status"] = "Ошибка активации"
                    test["error_text"] = str(ex)
                update_cells(test)
                page.update()
        # После активации пересчитываем статусы тестирования
        for test in tests_data:
            compute_final_test_status(test)
            update_cells(test)
            page.update()
        update_activate_button_state()

    activate_all_btn = ft.Button("Перевести в действующие", on_click=activate_all, disabled=True)

    def enable_run_button():
        has_rows = len(tests_data) > 0
        run_all_tests_btn.disabled = not has_rows
        page.update()

    def update_activate_button_state():
        has_agreed = any(test["status"] == "Согласован" for test in tests_data)
        activate_all_btn.disabled = not has_agreed
        page.update()

    def select_folder_and_fill_wrapper(e):
        select_folder_and_fill(e)

    auto_container.controls = [
        ft.Text("Массовое тестирование", weight=ft.FontWeight.BOLD, size=16),
        ft.Row([ft.Button("Заполнить таблицу из папки", on_click=select_folder_and_fill_wrapper),
                run_all_tests_btn, activate_all_btn]),
        ft.Divider(),
        ft.Text("Результаты тестов:", weight=ft.FontWeight.BOLD),
        ft.Row([table], scroll=ft.ScrollMode.AUTO),
        pdf_choice_panel,
    ]

    # ================== НАСТРОЙКИ ==================
    default_endpoints = {
        "Создание заявки на расчёт": "/calculate/",
        "Получение статуса калькуляции": "/calculate/{id}/",
        "Создание договора": "/create/",
        "Получение статуса договора": "/policy/{policyId}/status/",
        "Ссылка на форму оплаты": "/policy/{policyId}/acquiring/renins/",
        "Получение ПДФ образца": "/policy/{policyId}/pdfSample/",
        "Получение ПДФ документа": "/policy/{policyId}/pdf/",
        "Перевод в действующие": "/policy/{policyId}/register/",
    }

    method_endpoint_fields = {}
    settings_rows = []
    for method_name, default_url in default_endpoints.items():
        label = ft.Text(method_name, width=220)
        field = ft.TextField(value=default_url, width=400)
        method_endpoint_fields[method_name] = field
        settings_rows.append(ft.Row([label, field]))

    retry_count_field = ft.TextField(label="Количество попыток", value="5", width=200)
    retry_delay_field = ft.TextField(label="Пауза между попытками (сек)", value="3", width=200)
    timeout_field = ft.TextField(label="Тайм-аут запроса (сек)", value="30", width=200)
    status_poll_interval_field = ft.TextField(label="Интервал опроса статуса (сек)", value="10", width=200)
    fail_url_field = ft.TextField(label="fail_url", value="http://yandex.ru/fail_page/", width=400)
    success_url_field = ft.TextField(label="success_url", value="http://yandex.ru/success/", width=400)

    settings_rows.append(ft.Divider())
    settings_rows.append(ft.Text("Параметры повторов", weight=ft.FontWeight.BOLD))
    settings_rows.append(ft.Row([retry_count_field, retry_delay_field]))
    settings_rows.append(ft.Row([status_poll_interval_field]))
    settings_rows.append(ft.Row([timeout_field]))
    settings_rows.append(ft.Divider())
    settings_rows.append(ft.Text("Параметры ссылки на оплату", weight=ft.FontWeight.BOLD))
    settings_rows.append(ft.Row([fail_url_field, success_url_field]))

    settings_container.controls = [
        ft.Text("Настройки эндпоинтов", weight=ft.FontWeight.BOLD, size=16),
        ft.Text("Укажите относительные пути (или полные URL) для каждого запроса."),
    ] + settings_rows

    manual_container.visible = True
    auto_container.visible = False
    settings_container.visible = False
    manual_btn.disabled = True
    auto_btn.disabled = False
    settings_btn.disabled = False

    page.add(ft.Row([manual_btn, auto_btn, settings_btn]), manual_container, auto_container, settings_container)

ft.run(main)