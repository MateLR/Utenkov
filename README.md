# Utenkov
Практики по питоне с курса на elearn УрФУ
# Тестированиe
## Unitеsts
![image](https://user-images.githubusercontent.com/77449049/208920109-99b58c7c-c867-4efd-a2a5-c8d555c5c56e.png)
![image](https://user-images.githubusercontent.com/77449049/208920194-965decc3-92fe-4bcf-8076-bfa10103155a.png)
![image](https://user-images.githubusercontent.com/77449049/208920297-e437b826-46b7-46dd-b811-e52e1623b7c6.png)
![image](https://user-images.githubusercontent.com/77449049/208920440-eacb9252-a526-4e35-94c5-d63190f7cc55.png)


## Doctests
![image](https://user-images.githubusercontent.com/77449049/208919717-d09386f2-5527-4482-8f32-da55380f5657.png)
![image](https://user-images.githubusercontent.com/77449049/208919804-e174f5ea-675a-4890-9c90-b856395751e8.png)
![image](https://user-images.githubusercontent.com/77449049/208919863-52bccab8-3844-4f22-b955-077187484630.png)
![image](https://user-images.githubusercontent.com/77449049/208919933-dba77494-b9d8-45ed-805a-ef3a28e3d0ab.png)

# Замеры

## Выявление слабого места
![image](https://user-images.githubusercontent.com/77449049/208974612-d0a2787d-049f-46b8-a633-e7400b3c328a.png)
![image](https://user-images.githubusercontent.com/77449049/208971844-5873208e-85b9-411c-80cb-e64a379b84d7.png)
![image](https://user-images.githubusercontent.com/77449049/208971910-d63f4243-084b-4275-892f-6cf0c2c5e215.png)

Можно увидеть, что функция пребразования времени в datetime и в правдлу отнимает много времени

# Ускорение программы
Замерим время работы программы без профилизатора в обычных условиях - 39 секунд, однако профилизатор и ввод данных съедали почти половину времени
![image](https://user-images.githubusercontent.com/77449049/208978409-1875cccf-7e20-4662-a891-b0f13622e23b.png)
В моей программе работа класса вакансий и статистики немного отличается, поэтому попробуем вынести переменную со временем в часть вакансий,
а для статистики брать год разными способами.
- Первый просто брать 4 символа из стринга и преобразовывать в инт. - 18 секунд
```py
self.year = int(vacancy['published_at'][:4])
```
![image](https://user-images.githubusercontent.com/77449049/208979290-87fee578-3637-4cd7-843f-fbac349b3e5c.png)
- Остальные способы же упираются в использование datetime, только без сохранения всего спектра информации, а для нас это лишнее звено
в переводе строки (str) -> ~~datetime~~ -> целое число (int), но при этом для сортировки вакансий для таблицы вся информация о времени нужна
```py
datetime.strptime(s, '%Y-%m-%dT%H:%M:%S%z')
```
## Разделение файла
Написал скрипт для удаления старых файлов и разделение нашего csv файла по годам

//На скриншоте снизу нет документации к коду, в самом коде она есть
![image](https://user-images.githubusercontent.com/77449049/209677633-ee7febe7-f596-483a-aa7b-bf5b611920ea.png)

Разбитые файлы из файла vacancies_by_year.csv (тут старые файлы с индексами, я в будущем это заметил и убрал вывод индексов в csv):
[vacancies_by_2007.csv](https://github.com/MateLR/Utenkov/files/10308544/vacancies_by_2007.csv)
[vacancies_by_2008.csv](https://github.com/MateLR/Utenkov/files/10308560/vacancies_by_2008.csv)
[vacancies_by_2009.csv](https://github.com/MateLR/Utenkov/files/10308563/vacancies_by_2009.csv)
[vacancies_by_2010.csv](https://github.com/MateLR/Utenkov/files/10308564/vacancies_by_2010.csv)
[vacancies_by_2011.csv](https://github.com/MateLR/Utenkov/files/10308566/vacancies_by_2011.csv)
[vacancies_by_2012.csv](https://github.com/MateLR/Utenkov/files/10308567/vacancies_by_2012.csv)
[vacancies_by_2013.csv](https://github.com/MateLR/Utenkov/files/10308570/vacancies_by_2013.csv)
[vacancies_by_2014.csv](https://github.com/MateLR/Utenkov/files/10308574/vacancies_by_2014.csv)
[vacancies_by_2015.csv](https://github.com/MateLR/Utenkov/files/10308577/vacancies_by_2015.csv)
[vacancies_by_2016.csv](https://github.com/MateLR/Utenkov/files/10308580/vacancies_by_2016.csv)
[vacancies_by_2017.csv](https://github.com/MateLR/Utenkov/files/10308585/vacancies_by_2017.csv)
[vacancies_by_2018.csv](https://github.com/MateLR/Utenkov/files/10308590/vacancies_by_2018.csv)
[vacancies_by_2019.csv](https://github.com/MateLR/Utenkov/files/10308548/vacancies_by_2019.csv)
[vacancies_by_2020.csv](https://github.com/MateLR/Utenkov/files/10308549/vacancies_by_2020.csv)
[vacancies_by_2021.csv](https://github.com/MateLR/Utenkov/files/10308556/vacancies_by_2021.csv)
[vacancies_by_2022.csv](https://github.com/MateLR/Utenkov/files/10308559/vacancies_by_2022.csv)

## Multiprocessing
Создал новый скрипт с реализацией многопоточной обработки данных для анализа, новый анализ без городов представлен в файле report_m.pdf

//Не замерял через профилизатор по причине его съедания времени и неудобной реализации, так как приходится считывать информацию только с файла, потому что её много

Замеры "До" - 17.5 секунд:

![1](https://user-images.githubusercontent.com/77449049/209734893-de76e97a-a1c7-414f-a942-54ac5f982cce.png)

Замеры "После" - 4.5 секунд:

![2](https://user-images.githubusercontent.com/77449049/209734934-6681c913-b9d9-43e6-9b06-a241786cb0ad.png)

Можем заметить, что получилось ускорить нашу программу в 4 раза
