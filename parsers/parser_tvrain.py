import argparse
import math
import os
import time

import dateparser
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from tqdm import tqdm

from global_data import CHROMEDRIVER_BIN
from parsers.parser import Parser, ParseEntity, ParseResult


class TVRainParser(Parser):
    NEWS_ON_PAGE_NUM = 24
    SLEEP_TIME_MORE_BUTTON = 2  # seconds
    PAGES_NUM_BETWEEN_SLEEPS = 1
    SLEEP_TIME_NEWS_PAGE = 5  # seconds

    def __init__(self):
        super().__init__("https://tvrain.tv/news/")
        self.selenium_service = webdriver.ChromeService(executable_path=CHROMEDRIVER_BIN)

    def parse(self, news_num: int) -> ParseResult:
        selenium_driver = webdriver.Chrome(service=self.selenium_service)
        selenium_driver.maximize_window()
        selenium_driver.get(self.start_url)

        # "More" button click
        more_button_click_num = math.ceil(news_num / float(self.NEWS_ON_PAGE_NUM))
        print(f"[TVRainParser] Clicking to get more news ...")
        try:
            for _ in tqdm(range(more_button_click_num)):
                time.sleep(self.SLEEP_TIME_MORE_BUTTON)
                self.__move_to_bottom(selenium_driver)
                more_button = selenium_driver.find_element(By.CLASS_NAME, "button--outline")
                more_button.click()
        except (ElementClickInterceptedException, NoSuchElementException):
            print(f"[TVRainParser][Warning] Access to the button has been blocked ...")
        self.__move_to_bottom(selenium_driver)

        # Get news titles and metadata
        print(f"[TVRainParser] Parse titles ...")
        news_web_items = selenium_driver.find_elements(By.CLASS_NAME, "newsline_tile__headTitle")[:news_num]
        news_data = []
        for item in tqdm(news_web_items):
            news_link, news_title = self.__get_news_title(item)
            news_data.append([news_title, news_link])

        # Get news dates and texts
        print(f"[TVRainParser] Parse texts ...")
        for i, data in enumerate(tqdm(news_data)):
            if (i % self.PAGES_NUM_BETWEEN_SLEEPS) == 0:
                time.sleep(self.SLEEP_TIME_NEWS_PAGE)
            news_link = data[1]
            selenium_driver.get(news_link)
            news_text = self.__get_news_text(selenium_driver)
            news_date = self.__get_news_date(selenium_driver)
            data.append(news_text)
            data.append(news_date)

        # Create ParseResult
        parse_result = ParseResult()
        for id, item in enumerate(tqdm(news_data)):
            entity = ParseEntity(id=id, date=item[3], link=item[1], title=item[0], text=item[2])
            parse_result.add_entity(entity)

        return parse_result

    @staticmethod
    def __move_to_bottom(driver):
        ActionChains(driver).move_to_element(driver.find_element(By.CLASS_NAME, "footer-copy")).perform()

    @staticmethod
    def __get_news_title(driver):
        news_title_object = driver.find_element(By.TAG_NAME, "a")
        news_link = news_title_object.get_attribute('href')
        news_title = news_title_object.text
        return news_link, news_title

    @staticmethod
    def __get_news_text(driver):
        try:
            news_subtext = driver.find_element(By.CLASS_NAME, "document-lead").text
            news_text = driver.find_element(By.CLASS_NAME, "article-full__text").text
        except NoSuchElementException:
            return ""
        return '\n'.join([news_subtext, news_text, ])

    @staticmethod
    def __get_news_date(driver):
        dates_in_text = driver.find_elements(By.CLASS_NAME, "document-head__date")
        for date_in_text in dates_in_text:
            date_in_text = date_in_text.text
            news_date = dateparser.parse(date_in_text)
            if news_date:
                return news_date
        return None


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser(description="Parser to get fresh news articles from tvrain.tv")
    args_parser.add_argument("-n", "--news-num", required=True,
                             help="How many fresh news articles do you want to parse?")
    args_parser.add_argument("-o", "--output", required=True,
                             help="Output filename. Please use .csv or .xlsx extension")
    args = args_parser.parse_args()

    parser = TVRainParser()
    parse_data = parser.parse(int(args.news_num))

    extension = os.path.splitext(args.output)[1]
    if extension == '.csv':
        parse_data.to_csv(args.output)
    elif extension == '.xlsx':
        parse_data.to_excel(args.output)
    else:
        raise ValueError("Incorrect output file extension! Please use .csv or .xlsx")
