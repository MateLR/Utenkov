import csv
import multiprocessing
import concurrent.futures as pool
import re
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side
from jinja2 import Environment, FileSystemLoader
import pdfkit
import os


def exp_for_num(s: str):
    """Функция, котороая переводит строки с опытом в числа, которые в дальнейшем сравниваются
    Args:
        s (str): Принимает на вход одну переменную типа string, которая содержит в себе информацию об опыте работы
    Returns:
        int: возвращает числовое значение типа данных int, в соответствии с указанным значением опыта работы
    """
    s = re.findall(r'\d*\.\d+|\d+', s)
    return 0 if len(s) == 0 else int(s[0])


headings = ['№', 'Название', 'Описание', 'Навыки', 'Опыт работы', 'Премиум-вакансия', 'Компания',
            'Оклад', 'Название региона', 'Дата публикации вакансии']
currency = {"AZN": "Манаты",
            "BYR": "Белорусские рубли",
            "EUR": "Евро",
            "GEL": "Грузинский лари",
            "KGS": "Киргизский сом",
            "KZT": "Тенге",
            "RUR": "Рубли",
            "UAH": "Гривны",
            "USD": "Доллары",
            "UZS": "Узбекский сум"}
experience = {"noExperience": "Нет опыта",
              "between1And3": "От 1 года до 3 лет",
              "between3And6": "От 3 до 6 лет",
              "moreThan6": "Более 6 лет"}
bools = {"False": "Нет",
         "True": "Да"}
currency_to_rub = {
    "Манаты": 35.68,
    "Белорусские рубли": 23.91,
    "Евро": 59.90,
    "Грузинский лари": 21.74,
    "Киргизский сом": 0.76,
    "Тенге": 0.13,
    "Рубли": 1,
    "Гривны": 1.64,
    "Доллары": 60.66,
    "Узбекский сум": 0.0055,
}
functions_for_filter = {
    "Название": lambda vacancy, value: vacancy.name == value,
    "Описание": lambda vacancy, value: vacancy.description == value,
    "Компания": lambda vacancy, value: vacancy.employer_name == value,
    "Навыки": lambda vacancy, values: all(x in vacancy.key_skills for x in values.split(', ')),
    "Опыт работы": lambda vacancy, value: vacancy.experience_id == value,
    "Премиум-вакансия": lambda vacancy, value: vacancy.premium == value,
    "Название региона": lambda vacancy, value: vacancy.area_name == value,
    "Идентификатор валюты оклада": lambda vacancy, value: vacancy.salary.salary_currency == value,
    "Дата публикации вакансии": lambda vacancy, value: vacancy.published_at.strftime("%d.%m.%Y") == value,
    "Оклад": lambda vacancy, value: vacancy.salary.salary_from <= float(value) <= vacancy.salary.salary_to,
}
functions_for_sort = {
    "Название": lambda vacancy: vacancy.name,
    "Описание": lambda vacancy: vacancy.description,
    "Компания": lambda vacancy: vacancy.employer_name,
    "Навыки": lambda vacancy: len(vacancy.key_skills),
    "Опыт работы": lambda vacancy: exp_for_num(vacancy.experience_id),
    "Премиум-вакансия": lambda vacancy: vacancy.premium,
    "Название региона": lambda vacancy: vacancy.area_name,
    "Идентификатор валюты оклада": lambda vacancy: vacancy.salary.salary_currency,
    "Дата публикации вакансии": lambda vacancy: vacancy.published_at,
    "Оклад": lambda vacancy: vacancy.salary.mid_salary_in_rubles
}


class Salary:
    """Класс для представления зарплаты
    Attributes:
        salary_from (float): Нижняя граница вилки оклада
        salary_to (float): Верхняя граница вилки оклада
        salary_currency (str): Валюта оклада
        salary_gross (bool): Атрибут показывает есть ли налоговый вычет у зарплаты, по умолчанию значение False
        mid_salary_in_rubles (float): Среднее значение зарплаты в рублях
    """

    def __init__(self, salary: list):
        """Иницилизирует объект Salary, распаковывая все данные о зарплате, кроме налогового вычета
        Args:
            salary (list): Список данных о зарплате в порядке: Нижняя граница, Верхняя граница, Валюта
        """
        self.salary_from = float(salary[0])
        self.salary_to = float(salary[1])
        self.salary_currency = currency[salary[2]]
        self.salary_gross = False
        self.mid_salary_in_rubles = (self.salary_from + self.salary_to) / 2 * currency_to_rub[self.salary_currency]

    def add_gross(self, salary_gross: str):
        """Метод для изменения атрибута salary_gross, который нужно вызывать при наличии данной информации в строке
        Args:
            salary_gross (str): Строка с информацией о наличии налогового вычета
        """
        self.salary_gross = salary_gross == "True" or salary_gross == "Да"

    def to_string(self):
        """Преобразовывает всю информацию о зарплате в строку
        Returns (str): Информация о зарплате
        """
        return f'{"{:,d}".format(int(self.salary_from)).replace(",", " ")} - {"{:,d}".format(int(self.salary_to)).replace(",", " ")} ({self.salary_currency}) {"(С вычетом налогов)" if self.salary_gross else "(Без вычета налогов)"}'


class Vacancy(object):
    """Класс для представления Вакансии
    Attributes:
        name (str): Название вакансии
        salary (Salary): Вся информация о зарплате
        area_name (str): Название региона вакансии
        published_at (datetime): Дата публикации вакансии
        year (int): Год публикации вакансии
        description (str): Описание вакансии
        key_skills (list): Список навыков
        experience_id (str): Опыт работы требуемый для вакансии
        premium (bool): Примиальность вакансии
        employer_name (str): Название компании вакансии
    """

    def __init__(self, vacancy: dict):
        """Иницилизирует объект вакансии, распаковывает все данные и выполняет их конвертацию
        Args:
            vacancy (dict): Словарь с данными о вакансии
        """
        self.name = vacancy['name']
        self.salary = Salary(
            [vacancy['salary_from'], vacancy['salary_to'], vacancy['salary_currency']])
        self.area_name = vacancy['area_name']
        self.year = self.make_date_from_str(vacancy['published_at'])
        if len(vacancy) > 6:
            self.published_at = datetime.strptime(vacancy['published_at'], '%Y-%m-%dT%H:%M:%S%z')
            self.description = vacancy['description']
            self.key_skills = vacancy['key_skills'].split(';;')
            self.experience_id = experience[vacancy['experience_id']]
            self.premium = bools[vacancy['premium']]
            self.employer_name = vacancy['employer_name']
            self.salary.add_gross(vacancy['salary_gross'])

    @staticmethod
    def make_date_from_str(s: str):
        return int(s[:4])

    @staticmethod
    def cut_string(s: str):
        """Обрезает строку, если её длина больше 100 символов и добавляет многоточие в конце
        Args:
            s (str): Принимает на вход одну переменную типа string
        Returns:
            (str): Изменённая строка
        """
        if len(s) > 100:
            return s[:100] + '...'
        return s

    def get_row(self, number: int):
        """Преобразует всю информацию о вакансии в список для таблицы
        Args:
            number (int): Номер вакансии
        Returns:
            (list): Список данных о вакансии
        """
        return [number + 1, self.name, self.cut_string(self.description), self.cut_string('\n'.join(self.key_skills)),
                self.experience_id, self.premium, self.employer_name, self.salary.to_string(), self.area_name,
                self.published_at.strftime("%d.%m.%Y")]


class DataSet(object):
    """Класс, который преобразует csv файл в базу данных информации о вакансиях, и анализирует эту информацию
    Attributes:
        path_name (str): Директория файла
        vacancies_objects (list): Список, хранящий вакансии в виде объекта Vacancy
        vacancies_number (int): Количество вакансий
        salary_by_years (dict): Словарь с зарплатами по годам
        number_by_years (dict): Словарь с количеством вакансий по годам
        salary_by_years_job (dict): Словарь с зарплатами по годам, по выбранной профессии
        number_by_years_job (dict): Словарь с количеством вакансий по годам, по выбранной профессии
    """

    def __init__(self, path_name: str):
        """Инициализирует объект DataSet, преобразует файл с вакансиями в список вакансий
        Args:
            path_name: Директория файла
        """
        self.path_name = path_name
        self.vacancies_objects = []
        self.vacancies_number = 0
        self.job_name = ''
        self.salary_by_years = dict()
        self.number_by_years = dict()
        self.salary_by_years_job = dict()
        self.number_by_years_job = dict()

    def analyze(self, job_name: str):
        """Анализирует данные и добавляет их в DataSet с применением многопроцессорной обработки
        Args:
            job_name (str): Название профессии
        """
        self.job_name = job_name
        with pool.ProcessPoolExecutor(multiprocessing.cpu_count()) as executor:
            wait_complete = []
            for path in os.listdir(self.path_name):
                future = executor.submit(self.year_analyze, f"{self.path_name}/{path}")
                wait_complete.append(future)

        for result in pool.as_completed(wait_complete):
            item = result.result()
            self.salary_by_years[item[0]] = item[1]
            self.number_by_years[item[0]] = item[0]
            self.salary_by_years_job[item[0]] = item[3]
            self.number_by_years_job[item[0]] = item[2]

        self.print_analyze()

    def year_analyze(self, file_path):
        """Анализирует и сохраняет вакансии с файла одного года

        Args:
            file_path: Название файла и путь к нему
        """
        vacancies_objects = [Vacancy(x) for x in self.file_to_rows(file_path)]
        number_by_years = 0
        salary_by_years = 0
        number_by_years_job = 0
        salary_by_years_job = 0
        year = vacancies_objects[0].year
        for vac in vacancies_objects:
            number_by_years = number_by_years + 1
            salary_by_years = salary_by_years + vac.salary.mid_salary_in_rubles

            if vac.name.find(self.job_name) >= 0:
                number_by_years_job = number_by_years_job + 1
                salary_by_years_job = salary_by_years_job + vac.salary.mid_salary_in_rubles

        salary_by_years = int(salary_by_years / number_by_years) if \
            number_by_years != 0 else 0
        salary_by_years_job = int(salary_by_years_job / number_by_years_job) if \
            number_by_years_job != 0 else 0
        self.vacancies_objects += vacancies_objects
        return year, number_by_years, salary_by_years, number_by_years_job, salary_by_years_job

    def print_analyze(self):
        """Печатает в консоль данные с проведённого анализа вакансий
        """
        print(f"Динамика уровня зарплат по годам: {self.salary_by_years}")
        print(f"Динамика количества вакансий по годам: {self.number_by_years}")
        print(f"Динамика уровня зарплат по годам для выбранной профессии: {self.salary_by_years_job}")
        print(f"Динамика количества вакансий по годам для выбранной профессии: {self.number_by_years_job}")

    @staticmethod
    def file_to_rows(file_path):
        """Извлекает данные из csv таблицы и преобразует их в список словарей, подходящих для преобразования в объект Vacancy
        Returns (list): Список словарей

        Args:
            file_path: Название файла и путь к нему
        """
        r_file = open(file_path, encoding='utf-8-sig')
        file = csv.reader(r_file)
        text = [x for x in file]
        if len(text) < 2:
            print("Пустой файл" if len(text) < 1 else "Нет данных")
            quit()
        vacancy = text[0]
        r_file.close()
        return [dict(zip(vacancy, x)) for x in text[1:] if len([value for value in x if value]) == len(vacancy)]

    def sort(self, sort_params: str, is_sort_reverse=False):
        """Сортирует список вакансий по нужным требованиям
        Args:
            sort_params (str): Параметры сортировки, которые должны быть реализованы в словаре functions_for_sort
            is_sort_reverse (bool): Атрибут, который указывает на необходимость обратной сортировки
        """
        self.vacancies_objects = sorted(self.vacancies_objects, key=functions_for_sort[sort_params],
                                        reverse=is_sort_reverse)

    def get_rows(self, need_filter: bool, filter_params):
        """Преобразует список вакансий [Vacancy] в список списков [[]], содержащих данные о вакансии и фильтрует по параметру
        Args:
            need_filter (bool): Аргумент, указывающий на необходимость фильтрации
            filter_params: Параметр фильтрации в виде списка из двух элементов, где первый параметр, а второй значение
        Returns:
            (list): Список вакансий в виде списков
        """
        rows = []
        count = 0
        for i in range(self.vacancies_number):
            if need_filter:
                if not functions_for_filter[filter_params[0]](self.vacancies_objects[i], filter_params[1]):
                    continue
            rows.append(self.vacancies_objects[i].get_row(count))
            count += 1
        if need_filter and len(rows) < 1:
            print("Ничего не найдено")
            quit()
        return rows


class Report(object):
    """Класс для формирования отчётов о вакансиях в виде изображения, таблицы (.xlsx), файла (pdf)
    Attributes:
        job_name (str): Название профессии для анализа
        data_set (DataSet): База данных по вакансиям
        wb (Workbook): Таблица, которая преобразуется в .xlsx
        ws1 (WorkSheet): Первый лист таблицы
        fig (.Figure): Фигура изображения с анализом
        ax (~.axes.Axes): Список осей с анализом
    """

    def __init__(self, file_name: str, job_name: str):
        """Инициализирует объект Report
        Args:
            file_name (str): Название файла с информацией о вакансиях
            job_name (str): Название профессии для анализа
        """
        self.job_name = job_name
        self.data_set = DataSet(file_name)
        self.data_set.analyze(self.job_name)
        self.wb = Workbook()
        self.wb.active.title = "Статистика по годам"
        self.ws1 = self.wb.active
        self.fig, self.ax = plt.subplots(2)

    @staticmethod
    def rename_cities(s: str):
        """Переиминовывает входные названия городов, добавляя перенос строки в названия городов, состоящие из двух слов
        Args:
            s (str): принимает на вход одну переменную типа string, название города
        Returns:
            str: Название города, если в нём был пробел или дефис, тогда будет с переносом строки
        """
        s = s.replace(' ', '\n')
        s = s.replace('-', '-\n')
        return s

    def generate_image(self):
        """Генерирует и сохраняет изображение в директории
        """
        labels = list(self.data_set.salary_by_years.keys())
        average_salary = list(self.data_set.salary_by_years.values())
        job_salary = list(self.data_set.salary_by_years_job.values())
        average_number = list(self.data_set.number_by_years.values())
        job_number = list(self.data_set.number_by_years_job.values())

        x = np.arange(len(labels))
        width = 0.35

        self.ax[0].bar(x - width / 2, average_salary, width, label='средняя з/п')
        self.ax[0].bar(x + width / 2, job_salary, width, label=f'з/п {self.job_name}')
        self.ax[0].set_title('Уровень зарплат по годам', fontsize=10)
        self.ax[0].set_xticks(x, labels, fontsize=8)
        self.ax[0].tick_params(axis='y', labelsize=8)
        self.ax[0].tick_params(axis='x', labelrotation=90, labelsize=8)
        self.ax[0].grid(axis='y')
        self.ax[0].legend(fontsize=8)

        self.ax[1].bar(x - width / 2, average_number, width, label='Количество вакансий')
        self.ax[1].bar(x + width / 2, job_number, width, label=f'Количество вакансий\n{self.job_name}')
        self.ax[1].set_title('Количество вакансий по годам', fontsize=10)
        self.ax[1].set_xticks(x, labels, fontsize=8)
        self.ax[1].tick_params(axis='y', labelsize=8)
        self.ax[1].tick_params(axis='x', labelrotation=90, labelsize=8)
        self.ax[1].grid(axis='y')
        self.ax[1].legend(fontsize=8)

        self.fig.tight_layout()

        # self.fig.show()
        self.fig.savefig('graph_m.png')

    def generate_excel(self):
        """Генерирует и сохраняет таблицу в виде .xlsx файла с анализом
        """
        self.analyze_to_rows_xlsx()
        self.edit_sheet_style(self.ws1)
        self.edit_cols_width(self.ws1)
        self.wb.save("report_m.xlsx")

    def generate_pdf(self):
        """Генерирует и сохраняет pdf файл с изображением и таблицей с анализом
        """
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("html_template_m.html")
        tables = self.analyze_to_rows_html()
        pdf_template = template.render(
            {'name': self.job_name, 'headers1': tables[0], 'rows1': tables[1]})
        config = pdfkit.configuration(wkhtmltopdf=r'D:\wkhtmltopdf\bin\wkhtmltopdf.exe')
        pdfkit.from_string(pdf_template, 'report_m.pdf', configuration=config, options={"enable-local-file-access": ""})

    def analyze_to_rows_xlsx(self):
        """Преобразовывает словари с анализом из базы данных в строки для таблицы .xlsx
        """
        self.ws1.append(["Год", "Средняя зарплата", "Количество вакансий", f"Средняя зарплата - {self.job_name}",
                         f"Количество вакансий - {self.job_name}"])
        for year in self.data_set.salary_by_years.keys():
            self.ws1.append(
                [year, self.data_set.salary_by_years[year], self.data_set.number_by_years[year],
                 self.data_set.salary_by_years_job[year],
                 self.data_set.number_by_years_job[year]])

    def analyze_to_rows_html(self):
        """Преобразовывает словари с анализом из базы данных в строки для html файла, который генерирует таблицу для pdf файла
        """
        headers1 = ["Год", "Средняя зарплата", "Количество вакансий", f"Средняя зарплата - {self.job_name}",
                    f"Количество вакансий - {self.job_name}"]
        rows1 = []
        for year in self.data_set.salary_by_years.keys():
            rows1.append(
                [year, self.data_set.salary_by_years[year], self.data_set.number_by_years[year],
                 self.data_set.salary_by_years_job[year],
                 self.data_set.number_by_years_job[year]])
        return headers1, rows1

    @staticmethod
    def edit_sheet_style(ws):
        """Изменяет стилистику таблицы .xlsx
        Args:
            ws (WorkSheet): Лист для изменения стилистики таблицы
        """
        sd = Side(border_style='thin', color='000000')
        for el in ws['1']:
            el.font = Font(bold=True)
        for row in ws:
            for el in row:
                el.border = Border(left=sd, right=sd, top=sd, bottom=sd)

    @staticmethod
    def edit_cols_width(ws):
        """Изменяет ширину колонок таблицы .xlsx
        Args:
            ws (WorkSheet): Лист для изменения стилистики таблицы
        """
        dims = {}
        for row in ws.rows:
            for cell in row:
                if cell.value:
                    dims[cell.column_letter] = max((dims.get(cell.column_letter, 0), len(str(cell.value)) + 2))
        for col, value in dims.items():
            ws.column_dimensions[col].width = value


class InputConnect(object):
    """Класс для ввода информации пользователем и выбора необходимых действий
    """

    def __init__(self):
        """Иницилизирует объект класса InputConnect, принимает данные из консоли и передаёт их в необходимые классы
        """
        name = input("Введите название директории: ")
        job_name = input("Введите название профессии: ")
        start_time = datetime.now()
        x = Report(name, job_name)
        x.generate_image()
        x.generate_pdf()
        print(datetime.now() - start_time)


if __name__ == '__main__':
    InputConnect()
