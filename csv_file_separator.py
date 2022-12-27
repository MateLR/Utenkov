import pandas as pd
import os
import glob


class Separator(object):
    @staticmethod
    def separate_file_by_year_by_year(file_name: str):
        file_name = file_name
        file = pd.read_csv(file_name)
        file['years'] = file['published_at'].apply(lambda x: x[:4])
        years = file['years'].unique()
        for year in years:
            data = file[file['years'] == year]
            data.to_csv(f"temp_csv/vacancies_by_{year}.csv")
        print("Files for separate by year: " + years)

    @staticmethod
    def delete_files():
        files = glob.glob('temp_csv/*')
        for f in files:
            os.remove(f)
        print("Files were delete")


Separator().delete_files()
Separator().separate_file_by_year_by_year('vacancies_by_year.csv')