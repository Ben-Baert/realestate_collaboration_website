from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import re
import ast
from sortedcontainers import SortedSet


class HouseSoldError(Exception):
    pass


class Realo:
    def __init__(self, url):
        if "realo" not in url:
            raise ValueError("Url must be a realo url")
        self.url = url
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(10)
        self.driver.get(self.url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.quit()

    def seller(self):
        return self.driver.find_element_by_css_selector(
            """
            a.font-medium:nth-child(1)
            """).text

    def address(self):
        return (self
                .driver
                .find_element_by_css_selector(
                 """
                 #container
                 > div
                 > div:nth-child(1)
                 > div
                 > div.module.module-description
                 > header
                 > div
                 > h2
                 > span
                 """).text)

    def lat_lng(self):
        return [float(x) for x in ast.literal_eval(self
                                                   .driver
                                                   .find_element_by_css_selector(
                                                        """
                                                        #mediaViewer
                                                        """)
                                                    .get_attribute('data-latlng'))]

    def price(self):
        price = (self
                 .driver
                 .find_element_by_css_selector(
                    """
                    span.row:nth-child(1)
                    """)
                 .text[2:]
                 .replace(".", ""))
        try:
            return int(price)
        except ValueError:
            if price == "Huis niet te koop":
                raise HouseSoldError(
                    """
                    It looks like the house is no longer available.
                    Best to check manually though!
                    """)

    def area(self):
        inhabitable = None
        total = None
        for item in (self
                     .driver
                     .find_elements_by_css_selector(
                      """
                      .basic-details > div > div
                      """)):
            title = item.find_element_by_css_selector(".title")
            if title.text.lower() == "bewoonbaar":
                inhabitable = int(item
                                  .find_element_by_css_selector(".value")
                                  .text
                                  .replace("m2", "")
                                  .replace(".", ""))
            elif title.text.lower() == "grond":
                total = int(item
                            .find_element_by_css_selector(".value")
                            .text
                            .replace("m2", "")
                            .replace(".", ""))
            if inhabitable and total:
                break
        return inhabitable, total

    def information(self):
        for item in (self
                     .driver
                     .find_elements_by_css_selector(
                        """
                        #container
                        > div
                        > div.col.col-2-3.left.col-md-10.col-sm-12.push-md-1.col-xs-12
                        > div
                        > div.module.module-details
                        > ul
                        > li
                        """)):
            yield item.text.split("\n")

    def epc(self):
        for item in self.information():
            if item[0] == "EPC waarde":
                return item[1]

    def description(self):
        try:
            return self.driver.find_element_by_css_selector(
                """
                .module-description
                > p:nth-child(4)
                """).text
        except NoSuchElementException:
            return None

    def thumbnail_pictures(self):
        self.driver.find_element_by_css_selector(
            """
            #mediaViewer
            > ul.views
            > li.show
            > div
            > div
            """).click()
        images = self.driver.find_elements_by_css_selector(
            """
            div.pswp__carousel-item
            > a
            > img
            """)
        for image in images:
            yield image.get_attribute('src')

        self.driver.find_element_by_css_selector("""
            #mediaViewer
            > ul.views
            > li.show
            > div
            > div
            """).click()

    def main_pictures(self):
        images = SortedSet()
        self.driver.find_element_by_css_selector("#mediaViewer > ul.views > li.show > div > div").click()
        count = int(re.match("[0-9]+ / ([0-9]+)", self.driver.find_element_by_css_selector(".pswp__carousel-counter").text).group(1))
        for _ in range(count - 1):
            for img in self.driver.find_elements_by_css_selector("img.pswp__img"):
                url = img.get_attribute("src")
                images.add(url)
            self.driver.find_element_by_css_selector("button.pswp__button:nth-child(5)").click()
        self.driver.find_element_by_css_selector("#mediaViewer > ul.views > li.show > div > div").click()
        return images