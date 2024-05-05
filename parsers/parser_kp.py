import argparse
import math
import os
import time

import dateparser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, TimeoutException
from tqdm import tqdm

from global_data import CHROMEDRIVER_BIN
from parsers.parser import Parser, ParseEntity, ParseResult


class KPParser(Parser):
    NEWS_ON_PAGE_NUM = 15
    SLEEP_TIME_MORE_BUTTON = 5  # seconds
    PAGES_NUM_BETWEEN_SLEEPS = 1
    SLEEP_TIME_NEWS_PAGE = 5  # seconds

    def __init__(self):
        super().__init__('https://www.kp.ru/online/')
        self.selenium_service = webdriver.ChromeService(executable_path=CHROMEDRIVER_BIN)

    def parse(self, news_num: int) -> ParseResult:
        selenium_driver = webdriver.Chrome(service=self.selenium_service)
        selenium_driver.maximize_window()
        selenium_driver.get(self.start_url)
        selenium_driver.set_page_load_timeout(1000)

        # "More" button click
        more_button_click_num = math.ceil(news_num / float(self.NEWS_ON_PAGE_NUM))
        print(f"[KPParser] Clicking to get more news ...")
        try:
            for i in tqdm(range(more_button_click_num)):
                time.sleep(self.SLEEP_TIME_MORE_BUTTON)
                more_button = selenium_driver.find_element(By.CLASS_NAME, 'sc-abxysl-0')
                more_button.click()
        except (ElementClickInterceptedException, NoSuchElementException):
            print(f"[KPParser][Warning] Access to the button has been blocked ...")
        self.__move_to_bottom(selenium_driver)

        # Get news titles and metadata
        print(f"[KPParser] Parse titles ...")
        news_web_items = selenium_driver.find_elements(By.CLASS_NAME, "sc-1tputnk-13")[:news_num]
        news_data = []
        for item in tqdm(news_web_items):
            news_link = item.find_element(By.CLASS_NAME, "sc-1tputnk-2").get_attribute('href')
            news_title, news_subtitle = self.__get_news_title(item)
            news_tag = item.find_element(By.CLASS_NAME, "sc-1tputnk-11").text
            news_data.append([(news_title, news_subtitle), news_link, news_tag])

        # Get news dates and texts
        print(f"[KPParser] Parse texts ...")
        for i, data in enumerate(tqdm(news_data)):
            if (i % self.PAGES_NUM_BETWEEN_SLEEPS) == 0:
                time.sleep(self.SLEEP_TIME_NEWS_PAGE)
            try:
                news_link = data[1]
                selenium_driver.get(news_link)
                news_date = self.__get_news_date(selenium_driver)
                news_text = self.__get_news_text(selenium_driver)
                data.append(news_text)
                data.append(news_date)
            except TimeoutException:
                continue

        # Create ParseResult
        parse_result = ParseResult()
        for id, item in enumerate(tqdm(news_data)):
            entity = ParseEntity(id=id, date=item[4], link=item[1], tags=[item[2], ],
                                 title=item[0][0], text='\n'.join([item[0][1], item[3]]))
            parse_result.add_entity(entity)
        return parse_result

    @staticmethod
    def __move_to_bottom(driver):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        pass

    @staticmethod
    def __get_news_title(driver):
        news_title = driver.find_element(By.CLASS_NAME, "sc-1tputnk-2").text
        news_subtitle = driver.find_element(By.CLASS_NAME, "sc-1tputnk-3").text
        return news_title, news_subtitle

    @staticmethod
    def __get_news_text(driver):
        try:
            news_body = driver.find_element(By.CLASS_NAME, "sc-14f2vgk-1").text
        except NoSuchElementException:
            news_body = ''
        return news_body

    @staticmethod
    def __get_news_date(driver):
        dates_in_text = driver.find_elements(By.CLASS_NAME, "sc-j7em19-1")
        for date_in_text in dates_in_text:
            date_in_text = date_in_text.text
            news_date = dateparser.parse(date_in_text)
            if news_date:
                return news_date
        return None


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser(description="Parser to get fresh news articles from https://www.kp.ru/online/")
    args_parser.add_argument("-n", "--news-num", required=True,
                             help="How many fresh news articles do you want to parse?")
    args_parser.add_argument("-o", "--output", required=True,
                             help="Output filename. Please use .csv or .xlsx extension")
    args = args_parser.parse_args()

    parser = KPParser()
    parse_data = parser.parse(int(args.news_num))

    extension = os.path.splitext(args.output)[1]
    if extension == '.csv':
        parse_data.to_csv(args.output)
    elif extension == '.xlsx':
        parse_data.to_excel(args.output)
    else:
        raise ValueError("Incorrect output file extension! Please use .csv or .xlsx")
