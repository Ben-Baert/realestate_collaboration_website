from selenium import webdriver

class Realo:
    def __init__(self, url):
        self.driver = webdriver.PhantomJS()
        self.driver.get(url)

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
