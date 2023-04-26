import os
import random
import re
import time

from bs4 import BeautifulSoup
from hangul_utils import join_jamos
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

driver_path = 'C:/webdrivers/chromedriver.exe'
options = Options()
options.add_argument('--headless')
options.add_argument('--log-level=3')

driver = webdriver.Chrome(executable_path=driver_path, options=options)

while True:
    category = input("Enter the category you want to scrape (proverb, phrase, idiom): ").strip().lower()
    if category in ['proverb', 'phrase', 'idiom']:
        break
    else:
        print("Invalid category. Please enter 'proverb', 'phrase', or 'idiom'.")

while True:
    output_dir = input("Enter the directory where you want to save the scraped data: ").strip()
    try:
        os.makedirs(output_dir, exist_ok=True)
        break
    except Exception as e:
        print(f"Error creating directory: {e}")
        print("Please try again.")

consonants = ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
vowels = ['ㅏ', 'ㅑ', 'ㅓ', 'ㅕ', 'ㅗ', 'ㅛ', 'ㅜ', 'ㅠ', 'ㅡ', 'ㅣ']

while True:
    order = input("Enter the order you want to scrape (alphabetical, random): ").strip().lower()
    if order in ['alphabetical', 'random']:
        break
    else:
        print("Invalid order. Please enter 'alphabetical' or 'random'.")

char_combinations = [(c, v) for c in consonants for v in vowels]
if order == 'random':
    random.shuffle(char_combinations)

for consonant, vowel in tqdm(char_combinations, ncols=80, dynamic_ncols=True):
    combined_char = join_jamos(consonant + vowel)

    url = f"https://ko.dict.naver.com/#/topic/search?category1={category}"
    driver.get(url)
    time.sleep(1)

    wait = WebDriverWait(driver, 1)
    retry_attempts = 1

    for _ in range(retry_attempts):
        try:
            consonant_radio = wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//label[contains(text(), '{consonant}')]//input[@type='radio']")))
            driver.execute_script("arguments[0].click();", consonant_radio)

            vowel_radio = wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//label[contains(text(), '{vowel}')]//input[@type='radio']")))
            driver.execute_script("arguments[0].click();", vowel_radio)
            break
        except Exception as e:
            print(f"Error while clicking radio buttons (attempt {_ + 1}): {type(e).__name__} - {str(e)}")
    else:
        print(f"Failed to click radio buttons after {retry_attempts} attempts. Skipping this combination.")
        continue

    time.sleep(1)

    page_num = 1
    while True:
        url = f"https://ko.dict.naver.com/#/topic/search?category1={category}&consonant={consonant}&vowel={vowel}&page={page_num}"
        driver.get(url)
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        expression_elements = soup.select('.origin a.link')

        if not expression_elements:
            break

        output_data = ""

        for element in expression_elements:
            expression = element.text.strip()
            expression_url = 'https://ko.dict.naver.com' + element['href']

            driver.get(expression_url)
            time.sleep(1)

            expression_soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Remove unnecessary elements
            for workbook_btn in expression_soup.select("button#btnAddWordBook"):
                workbook_btn.decompose()
            for special_domain in expression_soup.select('span[class^="mean_addition specialDomain_"]'):
                special_domain.decompose()
            for related_words in expression_soup.select("dt.tit:-soup-contains('Related words')"):
                related_words.decompose()

            for old_pron_area in expression_soup.select('dl[class*="entry_pronounce my_old_pron_area"]'):
                old_pron_area.decompose()

            for play_area in expression_soup.select("div.play_area"):
                play_area.decompose()

            for example_translate in expression_soup.select('div[class^="example _word_mean_ex example_translate"]'):
                example_translate.decompose()

            mean_section = expression_soup.select_one('div.section.section_mean.is-source._section_mean._data_index_1')

            if mean_section is None:
                print(f"Meaning section not found for expression: {expression}")
                continue

            # Scrape texts inside the div with class="component_entry"
            component_entries = expression_soup.select('div.component_entry')
            if component_entries:
                for component_entry in component_entries:
                    component_entry_text = component_entry.text.strip()
                    component_entry_text = re.sub('\n{2,}', '\n', component_entry_text)
                    output_data += '\t\t' + component_entry_text + '\n'

            meanings = mean_section.select('.mean_list .mean_item:not([class^="mean_addition specialDomain_"])')
            if not meanings:
                print(f"No meanings found for expression: {expression}")
                continue

            for meaning in meanings:
                meaning_text = meaning.text.strip()
                meaning_text = re.sub('\n{2,}', '\n', meaning_text)
                meaning_text = re.sub('\n.+example _word_mean_ex example_translate.+', '', meaning_text)
                output_data += '\t' + meaning_text + '\n'

            driver.back()
            time.sleep(1)

            # Add vocabulary end marker
            output_data += "\n"

        if output_data.strip():
            output_data = output_data.strip()
            output_file = os.path.join(output_dir, f"{combined_char}-{page_num}.txt")

            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(output_data)

        page_num += 1

driver.quit()
