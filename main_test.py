from unittest import TestCase
from main import DataSet, Salary, functions_for_filter


class DataSetTests(TestCase):
    def test_dataset_attributes(self):
        dataset = DataSet("vacancies_medium.csv")
        self.assertEqual(type(dataset).__name__, "DataSet")
        self.assertEqual(type(dataset.vacancies_objects[0]).__name__, "Vacancy")
        self.assertEqual(dataset.vacancies_number, len(dataset.vacancies_objects))

    def test_dataset_analyze(self):
        dataset = DataSet("vacancies_medium.csv")
        dataset.analyze("Аналитик")
        self.assertNotEqual(dataset.number_by_years_job[2022], dataset.number_by_years[2022])
        self.assertNotEqual(dataset.salary_by_years[2022], dataset.salary_by_years_job[2022])
        self.assertEqual(dataset.salary_by_area["Екатеринбург"], 95270)

    def test_dataset_sort(self):
        def check_sort(sort_params: str):
            dataset.sort(sort_params)
            first = dataset.vacancies_objects[0].name
            dataset.sort(sort_params, True)
            second = dataset.vacancies_objects[0].name
            self.assertNotEqual(first, second)

        dataset = DataSet("vacancies_big.csv")
        check_sort("Название")
        check_sort("Описание")
        check_sort("Компания")
        check_sort("Опыт работы")
        check_sort("Премиум-вакансия")
        check_sort("Идентификатор валюты оклада")
        check_sort("Дата публикации вакансии")
        check_sort("Оклад")

    def test_dataset_filter(self):
        functions_for_checking = {
            "Название": lambda vacancy, value: vacancy[1] == value,
            "Описание": lambda vacancy, value: vacancy[2] == value,
            "Компания": lambda vacancy, value: vacancy[6] == value,
            "Навыки": lambda vacancy, values: all(x in vacancy[3].split('\n') for x in values.split(', ')),
            "Опыт работы": lambda vacancy, value: vacancy[4] == value,
            "Премиум-вакансия": lambda vacancy, value: vacancy[5] == value,
            "Название региона": lambda vacancy, value: vacancy[8] == value,
            "Дата публикации вакансии": lambda vacancy, value: vacancy[9] == value,
        }

        def check_filter(filter_name: str, filter_value: str):
            x = dataset.get_rows(True, [filter_name, filter_value])
            self.assertTrue(functions_for_checking[filter_name](x[0], filter_value))

        dataset = DataSet("vacancies_big.csv")
        check_filter("Название", "Senior DevOps (проектная работа)")
        check_filter("Компания", "Enface")
        check_filter("Навыки", "Ethereum")
        check_filter("Опыт работы", "От 1 года до 3 лет")
        check_filter("Премиум-вакансия", "Да")
        check_filter("Название региона", "Москва")
        check_filter("Дата публикации вакансии", "06.07.2022")


class SalaryTests(TestCase):
    def test_salary_init(self):
        salary = Salary([10.0, 20.4, 'RUR'])
        self.assertEqual(salary.salary_to, 20.4)
        self.assertEqual(salary.salary_from, 10)
        self.assertEqual(salary.salary_currency, 'Рубли')

    def test_salary_init_all_str(self):
        salary = Salary(['10.0', '20', 'USD'])
        self.assertEqual(salary.salary_to, 20)
        self.assertEqual(salary.salary_from, 10)
        self.assertEqual(salary.salary_currency, 'Доллары')

    def test_salary_add_gross(self):
        salary = Salary([10.0, 20.4, 'RUR'])
        self.assertEqual(salary.salary_gross, False)
        salary.add_gross("True")
        self.assertTrue(salary.salary_gross)

    def test_salary_mid_in_rub(self):
        self.assertEqual(Salary(['10.0', '20', 'USD']).mid_salary_in_rubles, 909.9)
        self.assertEqual(Salary(['0', '1000', 'EUR']).mid_salary_in_rubles, 29950)
        self.assertEqual(Salary(['10.0', '20', 'RUR']).mid_salary_in_rubles, 15)
        self.assertEqual(Salary(['0', '1000', 'RUR']).mid_salary_in_rubles, 500)

    def test_salary_to_string(self):
        self.assertEqual(Salary(['10.0', '20000', 'USD']).to_string(), '10 - 20 000 (Доллары) (Без вычета налогов)')
