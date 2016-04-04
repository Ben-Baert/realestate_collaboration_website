from selenium import webdriver
import re
from sortedcontainers import SortedSet


class Realo:
    def __init__(self, url):
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

    def price(self):
        return int(self
                   .driver
                   .find_element_by_css_selector(
                        """
                        span.row:nth-child(1)
                        """)
                   .text[2:]
                   .replace(".", ""))

    def inhabitable_area(self):
        return int(self
                   .driver
                   .find_element_by_css_selector(
                    """
                    #container
                    > div
                    > div:nth-child(1)
                    > div
                    > div.module.module-header
                    > div:nth-child(2)
                    > div
                    > div
                    > div:nth-child(3)
                    > div.row.value
                    > span
                    """)
                   .text
                   .replace("m2", ""))

    def total_area(self):
        return int(self
                   .driver
                   .find_element_by_css_selector(
                    """
                    #container
                    > div
                    > div.col.col-2-3.left.col-md-10.col-sm-12.push-md-1.col-xs-12
                    > div > div.module.module-header
                    > div:nth-child(2)
                    > div
                    > div
                    > div:nth-child(4)
                    > div.row.value
                    > span
                    """)
                   .text
                   .replace("m2", "")
                   .replace(".", ""))

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
        return self.driver.find_element_by_css_selector(
            """
            .module-description > p:nth-child(4)
            """).text

    def thumbnail_pictures(self):
        self.driver.find_element_by_css_selector("#mediaViewer > ul.views > li.show > div > div").click()
        images = self.driver.find_elements_by_css_selector(
            """
            div.pswp__carousel-item
            > a
            > img
            """)
        for image in images:
            yield image.get_attribute('src')
        self.driver.find_element_by_css_selector("#mediaViewer > ul.views > li.show > div > div").click()

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