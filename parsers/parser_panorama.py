import argparse
import os
import time
from enum import Enum

from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from tqdm import tqdm

from global_data import CHROMEDRIVER_BIN
from parsers.parser import Parser, ParseEntity, ParseResult


class PanoramaCategories(str, Enum):
    POLITICS = "politics"
    SOCIETY = "society"


class PanoramaParser(Parser):

    PAGES_NUM_BETWEEN_SLEEPS = 1
    SLEEP_TIME_NEWS_PAGE = 5  # seconds

    def __init__(self, category: PanoramaCategories = None, from_date: datetime = None):
        self.current_date = datetime.today() if from_date is None else from_date
        self.category = category
        super().__init__(self.get_current_news_page_link())
        self.selenium_service = webdriver.ChromeService(executable_path=CHROMEDRIVER_BIN)

    def get_current_news_page_link(self):
        return f"https://panorama.pub/{self.category}/{self.current_date.strftime('%d-%m-%Y')}"

    def parse(self, news_num: int) -> ParseResult:
        selenium_driver = webdriver.Chrome(service=self.selenium_service)
        selenium_driver.maximize_window()

        print(f"[PanoramaParser] Parse titles ...")
        news_data = []
        current_url = self.start_url
        progress_bar = tqdm(total=news_num)
        while len(news_data) < news_num:
            selenium_driver.get(current_url)
            for news_block in selenium_driver.find_elements(By.CLASS_NAME, "flex.flex-col.rounded-md.mb-2"):
                news_link = news_block.get_attribute('href')
                news_title = news_block.text.split('\n')[-1]
                news_data.append([news_title, news_link, self.current_date])
                progress_bar.update(1)
            self.current_date -= timedelta(1)
            current_url = self.get_current_news_page_link()
        news_data = news_data[:news_num]

        # Get news dates and texts
        print(f"[PanoramaParser] Parse texts ...")
        for i, data in enumerate(tqdm(news_data)):
            if (i % self.PAGES_NUM_BETWEEN_SLEEPS) == 0:
                time.sleep(self.SLEEP_TIME_NEWS_PAGE)
            news_link = data[1]
            selenium_driver.get(news_link)
            news_text = self.__get_news_text(selenium_driver)
            data.append(news_text)

        # Create ParseResult
        parse_result = ParseResult()
        for id, item in enumerate(tqdm(news_data)):
            entity = ParseEntity(id=id, date=item[2], link=item[1],
                                 title=item[0], text=item[3], tags=[f"{self.category}", ])
            parse_result.add_entity(entity)

        return parse_result

    @staticmethod
    def __get_news_text(driver):
        return driver.find_element(By.CLASS_NAME, "entry-contents.pr-0").text


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser(description="Parser to get fresh news articles from panorama.pub")
    args_parser.add_argument("-n", "--news-num", required=True, type=int,
                             help="How many fresh news articles do you want to parse?")
    args_parser.add_argument("-o", "--output", required=True,
                             help="Output filename. Please use .csv or .xlsx extension")
    args = args_parser.parse_args()

    news_num = args.news_num
    categories = [PanoramaCategories.POLITICS, PanoramaCategories.SOCIETY, ]
    news_step = news_num // len(categories)
    parse_data_list = []
    for i, category in enumerate(categories):
        print(f'Parsing category: {category}')
        parser = PanoramaParser(category=category)
        parse_data = parser.parse(news_step if i < len(categories) - 1 else news_num)
        parse_data_list.append(parse_data)
        news_num -= news_step
    for parse_data in parse_data_list[1:]:
        parse_data_list[0] += parse_data
    parse_data = parse_data_list[0]
    extension = os.path.splitext(args.output)[1]
    if extension == '.csv':
        parse_data.to_csv(args.output)
    elif extension == '.xlsx':
        parse_data.to_excel(args.output)
    else:
        raise ValueError("Incorrect output file extension! Please use .csv or .xlsx")
