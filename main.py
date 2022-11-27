import csv
import re
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side
from jinja2 import Environment, FileSystemLoader
import prettytable
from prettytable import PrettyTable
import pdfkit


def delete_spaces(s: str):
    return ' '.join(s.split())


def cut_string(s: str):
    if len(s) > 100:
        return s[:100] + '...'
    return s


def exp_for_num(s: str):
    s = re.findall(r'\d*\.\d+|\d+', s)
    return 0 if len(s) == 0 else int(s[0])


def change_string(s: str):
    s = s.replace('\n', ';;')
    return ' '.join(re.sub("<[^>]*>", "", s).split())


def rename_cities(s: str):
    s = s.replace(' ', '\n')
    s = s.replace('-', '-\n')
    return s


def check_file_for_empty(len: int):
    if len < 2:
        print("Пустой файл" if len < 1 else "Нет данных")
        quit()


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
    def __init__(self, salary):
        self.salary_from = float(salary[0])
        self.salary_to = float(salary[1])
        self.salary_currency = currency[salary[2]]
        self.salary_gross = False
        self.mid_salary_in_rubles = (self.salary_from + self.salary_to) / 2 * currency_to_rub[self.salary_currency]

    def add_gross(self, salary_gross):
        self.salary_gross = bools[salary_gross]

    def to_string(self):
        return f'{"{:,d}".format(int(self.salary_from)).replace(",", " ")} - {"{:,d}".format(int(self.salary_to)).replace(",", " ")} ({self.salary_currency}) {"(Без вычета налогов)" if self.salary_gross != "Нет" else "(С вычетом налогов)"}'


class Vacancy(object):
    def __init__(self, vacancy):
        self.name = vacancy['name']
        self.salary = Salary(
            [vacancy['salary_from'], vacancy['salary_to'], vacancy['salary_currency']])
        self.area_name = vacancy['area_name']
        self.published_at = datetime.strptime(vacancy['published_at'], '%Y-%m-%dT%H:%M:%S%z')
        self.year = int(self.published_at.strftime("%Y"))
        if len(vacancy) > 6:
            self.description = vacancy['description']
            self.key_skills = vacancy['key_skills'].split(';;')
            self.experience_id = experience[vacancy['experience_id']]
            self.premium = bools[vacancy['premium']]
            self.employer_name = vacancy['employer_name']
            self.salary.add_gross(vacancy['salary_gross'])

    def get_row(self, number: int):
        return [number + 1, self.name, cut_string(self.description), cut_string('\n'.join(self.key_skills)),
                self.experience_id, self.premium, self.employer_name, self.salary.to_string(), self.area_name,
                self.published_at.strftime("%d.%m.%Y")]


class DataSet(object):
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.vacancies_objects = [Vacancy(x) for x in self.file_to_rows()]
        self.vacancies_number = len(self.vacancies_objects)
        self.salary_by_years = dict()
        self.number_by_years = dict()
        self.salary_by_years_job = dict()
        self.number_by_years_job = dict()
        self.salary_by_area = dict()
        self.share_number_by_area = dict()

    def analyze(self, job_name: str):
        self.fill_analyze_set(job_name)

        self.edit_analyze_set()

        self.print_analyze()

    def print_analyze(self):
        print(f"Динамика уровня зарплат по годам: {self.salary_by_years}")
        print(f"Динамика количества вакансий по годам: {self.number_by_years}")
        print(f"Динамика уровня зарплат по годам для выбранной профессии: {self.salary_by_years_job}")
        print(f"Динамика количества вакансий по годам для выбранной профессии: {self.number_by_years_job}")
        print(f"Уровень зарплат по городам (в порядке убывания): {self.salary_by_area}")
        print(f"Доля вакансий по городам (в порядке убывания): {self.share_number_by_area}")

    def fill_analyze_set(self, job_name: str):
        for vac in self.vacancies_objects:
            if vac.year not in self.number_by_years:
                self.number_by_years_job[vac.year] = 0
                self.salary_by_years_job[vac.year] = 0
                self.number_by_years[vac.year] = 0
                self.salary_by_years[vac.year] = 0
            if vac.area_name not in self.salary_by_area:
                self.share_number_by_area[vac.area_name] = 0
                self.salary_by_area[vac.area_name] = 0

            self.number_by_years[vac.year] = self.number_by_years[vac.year] + 1
            self.salary_by_years[vac.year] = self.salary_by_years[vac.year] + vac.salary.mid_salary_in_rubles
            self.share_number_by_area[vac.area_name] = self.share_number_by_area[vac.area_name] + 1
            self.salary_by_area[vac.area_name] = self.salary_by_area[vac.area_name] + vac.salary.mid_salary_in_rubles

            if vac.name.find(job_name) >= 0:
                self.number_by_years_job[vac.year] = self.number_by_years_job[vac.year] + 1
                self.salary_by_years_job[vac.year] = self.salary_by_years_job[
                                                         vac.year] + vac.salary.mid_salary_in_rubles

    def edit_analyze_set(self):
        for key in self.salary_by_years.keys():
            self.salary_by_years[key] = int(self.salary_by_years[key] / self.number_by_years[key]) if \
                self.number_by_years[key] != 0 else 0
        for key in self.salary_by_years_job.keys():
            self.salary_by_years_job[key] = int(self.salary_by_years_job[key] / self.number_by_years_job[key]) if \
                self.number_by_years_job[key] != 0 else 0

        areas = []
        for key in self.salary_by_area.keys():
            self.salary_by_area[key] = int(self.salary_by_area[key] / self.share_number_by_area[key])
            self.share_number_by_area[key] = round(self.share_number_by_area[key] / self.vacancies_number, 4)
            if self.share_number_by_area[key] < 0.01:
                areas.append(key)
        for key in areas:
            del self.salary_by_area[key]
            del self.share_number_by_area[key]

        self.salary_by_area = dict(sorted(self.salary_by_area.items(), key=lambda x: x[1], reverse=True)[:10])
        self.share_number_by_area = dict(
            sorted(self.share_number_by_area.items(), key=lambda x: x[1], reverse=True)[:10])

    def file_to_rows(self):
        r_file = open(self.file_name, encoding='utf-8-sig')
        file = csv.reader(r_file)
        text = [x for x in file]
        check_file_for_empty(len(text))
        vacancy = text[0]
        return [dict(zip(vacancy, [change_string(s) for s in x if s])) for x in text[1:] if
                len([value for value in x if value]) == len(vacancy)]

    def sort(self, sort_params, is_sort_reverse: bool):
        self.vacancies_objects = sorted(self.vacancies_objects, key=functions_for_sort[sort_params],
                                        reverse=is_sort_reverse)

    def get_rows(self, need_filter: bool, filter_params):
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
    def __init__(self, file_name: str, job_name: str):
        self.job_name = job_name
        self.data_set = DataSet(file_name)
        self.data_set.analyze(self.job_name)
        self.wb = Workbook()
        self.wb.active.title = "Статистика по годам"
        self.ws1 = self.wb.active
        self.ws2 = self.wb.create_sheet("Статистика по городам")
        self.fig, self.ax = plt.subplots(2, 2)

    def generate_image(self):
        labels = list(self.data_set.salary_by_years.keys())
        average_salary = list(self.data_set.salary_by_years.values())
        job_salary = list(self.data_set.salary_by_years_job.values())
        average_number = list(self.data_set.number_by_years.values())
        job_number = list(self.data_set.number_by_years_job.values())
        cities_salary = [rename_cities(x) for x in self.data_set.salary_by_area.keys()]
        salaries_city = list(self.data_set.salary_by_area.values())
        cities_share = ["Другие"] + list(self.data_set.share_number_by_area.keys())
        shares_city = list(self.data_set.share_number_by_area.values())
        shares_city = [1 - sum(shares_city)] + shares_city

        x = np.arange(len(labels))
        y = np.arange(len(cities_salary))
        width = 0.35

        self.ax[0, 0].bar(x - width / 2, average_salary, width, label='средняя з/п')
        self.ax[0, 0].bar(x + width / 2, job_salary, width, label=f'з/п {self.job_name}')
        self.ax[0, 0].set_title('Уровень зарплат по годам', fontsize=10)
        self.ax[0, 0].set_xticks(x, labels, fontsize=8)
        self.ax[0, 0].tick_params(axis='y', labelsize=8)
        self.ax[0, 0].tick_params(axis='x', labelrotation=90, labelsize=8)
        self.ax[0, 0].grid(axis='y')
        self.ax[0, 0].legend(fontsize=8)

        self.ax[0, 1].bar(x - width / 2, average_number, width, label='Количество вакансий')
        self.ax[0, 1].bar(x + width / 2, job_number, width, label=f'Количество вакансий\n{self.job_name}')
        self.ax[0, 1].set_title('Количество вакансий по годам', fontsize=10)
        self.ax[0, 1].set_xticks(x, labels, fontsize=8)
        self.ax[0, 1].tick_params(axis='y', labelsize=8)
        self.ax[0, 1].tick_params(axis='x', labelrotation=90, labelsize=8)
        self.ax[0, 1].grid(axis='y')
        self.ax[0, 1].legend(fontsize=8)

        self.ax[1, 0].barh(y, salaries_city, align='center')
        self.ax[1, 0].set_yticks(y, labels=cities_salary)
        self.ax[1, 0].tick_params(axis='y', labelsize=6)
        self.ax[1, 0].tick_params(axis='x', labelsize=8)
        self.ax[1, 0].invert_yaxis()
        self.ax[1, 0].set_title('Уровень зарплат по городам', fontsize=10)
        self.ax[1, 0].grid(axis='x')

        self.ax[1, 1].pie(shares_city, labels=cities_share, textprops={'fontsize': 6}, startangle=-20)
        self.ax[1, 1].set_title('Доля зарплат по городам', fontsize=10)

        self.fig.tight_layout()

        # self.fig.show()
        self.fig.savefig('graph.png')

    def generate_excel(self):
        self.analyze_to_rows()
        self.edit_sheet_style(self.ws1)
        self.edit_sheet_style(self.ws2)
        self.ws2.insert_cols(3)
        self.ws2.column_dimensions['C'].width = 2
        for row in self.ws2['E2':'E11']:
            for el in row:
                el.number_format = '0.00%'
        self.edit_cols_width(self.ws1)
        self.edit_cols_width(self.ws2)
        self.wb.save("report.xlsx")

    def generate_pdf(self):
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("html_template.html")
        tables = self.analyze_to_rows_html()
        pdf_template = template.render(
            {'name': self.job_name, 'headers1': tables[0], 'headers2': tables[1], 'rows1': tables[2],
             'rows2': tables[3]})
        config = pdfkit.configuration(wkhtmltopdf=r'D:\wkhtmltopdf\bin\wkhtmltopdf.exe')
        pdfkit.from_string(pdf_template, 'report.pdf', configuration=config, options={"enable-local-file-access": ""})

    def analyze_to_rows(self):
        self.ws1.append(["Год", "Средняя зарплата", "Количество вакансий", f"Средняя зарплата - {self.job_name}",
                         f"Количество вакансий - {self.job_name}"])
        for year in self.data_set.salary_by_years.keys():
            self.ws1.append(
                [year, self.data_set.salary_by_years[year], self.data_set.number_by_years[year],
                 self.data_set.salary_by_years_job[year],
                 self.data_set.number_by_years_job[year]])
        self.ws2.append(["Город", "Уровень зарплат", "Город", "Доля вакансий"])
        salary_items = [(k, v) for k, v in self.data_set.salary_by_area.items()]
        share_number_items = [(k, v) for k, v in self.data_set.share_number_by_area.items()]
        for i in range(10):
            self.ws2.append([salary_items[i][0], salary_items[i][1],
                             share_number_items[i][0],
                             share_number_items[i][1]])

    def analyze_to_rows_html(self):
        headers1 = ["Год", "Средняя зарплата", "Количество вакансий", f"Средняя зарплата - {self.job_name}",
                    f"Количество вакансий - {self.job_name}"]
        rows1 = []
        for year in self.data_set.salary_by_years.keys():
            rows1.append(
                [year, self.data_set.salary_by_years[year], self.data_set.number_by_years[year],
                 self.data_set.salary_by_years_job[year],
                 self.data_set.number_by_years_job[year]])
        headers2 = ["Город", "Уровень зарплат", "", "Город", "Доля вакансий"]
        salary_items = [(k, v) for k, v in self.data_set.salary_by_area.items()]
        share_number_items = [(k, v) for k, v in self.data_set.share_number_by_area.items()]
        rows2 = []
        for i in range(10):
            rows2.append([salary_items[i][0], salary_items[i][1], "",
                          share_number_items[i][0],
                          f'{round(share_number_items[i][1] * 100, 3)}%'])
        return headers1, headers2, rows1, rows2

    @staticmethod
    def edit_sheet_style(ws):
        sd = Side(border_style='thin', color='000000')
        for el in ws['1']:
            el.font = Font(bold=True)
        for row in ws:
            for el in row:
                el.border = Border(left=sd, right=sd, top=sd, bottom=sd)

    @staticmethod
    def edit_cols_width(ws):
        dims = {}
        for row in ws.rows:
            for cell in row:
                if cell.value:
                    dims[cell.column_letter] = max((dims.get(cell.column_letter, 0), len(str(cell.value)) + 2))
        for col, value in dims.items():
            ws.column_dimensions[col].width = value


class TableOfDataSet(object):
    def __init__(self):
        self.name: str = input("Введите название файла: ")
        self.filter_params = input("Введите параметр фильтрации: ")
        self.sort_params = input("Введите параметр сортировки: ")
        self.is_sort_reverse = input("Обратный порядок сортировки (Да / Нет): ")
        self.numbers = input("Введите диапазон вывода: ").split()
        self.new_fields = [x for x in input("Введите требуемые столбцы: ").split(', ') if x != '']
        self.new_fields.append('№')
        self.my_table = PrettyTable(border=True, header=True, hrules=prettytable.ALL)
        self.need_filter = len(self.filter_params) > 0
        self.needSort = len(self.sort_params) > 0
        self.check_inputs()
        self.data_set = DataSet(self.name)
        if len(self.numbers) < 2:
            self.numbers = [1, self.data_set.vacancies_number + 1] if len(self.numbers) == 0 else [
                self.numbers[0],
                self.data_set.vacancies_number + 1]
        if self.needSort:
            self.data_set.sort(self.sort_params, self.is_sort_reverse)
        self.table_fill()

    def check_inputs(self):
        if self.need_filter:
            if not ':' in self.filter_params:
                print("Формат ввода некорректен")
                quit()
            self.filter_params = self.filter_params.split(': ', 1)
            if not self.filter_params[0] in functions_for_filter.keys():
                print("Параметр поиска некорректен")
                quit()
        if self.needSort and not self.sort_params in functions_for_sort.keys():
            print("Параметр сортировки некорректен")
            quit()
        if not self.is_sort_reverse in ["Да", "Нет", ""]:
            print("Порядок сортировки задан некорректно")
            quit()
        self.is_sort_reverse = True if self.is_sort_reverse == "Да" else False

    def table_fill(self):
        self.my_table.field_names = headings
        self.my_table.add_rows(self.data_set.get_rows(self.need_filter, self.filter_params))
        self.my_table.align = "l"
        self.my_table.max_width = 20
        self.new_fields = self.new_fields if len(self.new_fields) > 1 else self.my_table.field_names
        print(self.my_table.get_string(start=int(self.numbers[0]) - 1, end=int(self.numbers[1]) - 1,
                                       fields=self.new_fields))


class InputConnect(object):
    def __init__(self):
        report_type = False if input("Введите данные для печати: ") == "Статистика" else True
        if report_type:
            x = TableOfDataSet()
        else:
            self.name: str = input("Введите название файла: ")
            self.job_name = input("Введите название профессии: ")
            x = Report(self.name, self.job_name)
            x.generate_image()
            x.generate_pdf()


InputConnect()
