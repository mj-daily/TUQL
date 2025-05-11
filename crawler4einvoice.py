#%%
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from time import sleep
import json
# Set up Edge options
options = Options()
options.use_chromium = True # Ensure Chromium-based Edge is used

# Set up Edge WebDriver service
service = Service('./edgedriver_linux64/msedgedriver')  # Replace with the correct absolute path to the msedgedriver executable

#%%
# Initialize WebDriver
driver = webdriver.Edge(service=service, options=options)
driver.maximize_window()
driver.get('https://www.einvoice.nat.gov.tw/accounts/login/mw?login_challenge=')
sleep(3)
en_button = driver.find_element(By.XPATH, '//a[@role="button" and @title="EN"]')
en_button.click()
sleep(1)
with open('einvoice_accounts.json', 'r') as f:
    info = json.load(f)
driver.find_element(By.NAME, value='mobile_phone').send_keys(info['phone'])
driver.find_element(By.NAME, value='password'    ).send_keys(info['password'])
driver.find_element(By.ID  , value='captcha'     ).send_keys(input('captcha'))
sleep(1)
driver.find_element(By.ID  , value='submitBtn'   ).click()
sleep(15)
driver.find_element(By.XPATH, '//button[@title="Inquiry"]').click()
sleep(1)

# Find the dropdown element by its ID
dropdown = driver.find_element(By.ID, 'SelectSizes')

# Select the "100" option
for option in dropdown.find_elements(By.TAG_NAME, 'option'):
    if option.get_attribute('value') == '100':
        option.click()
        sleep(1)
        break

# Find the button with the specified attributes and click it
execute_button = driver.find_element(By.XPATH, '//button[@class="btn px-1 bg-gray btn-outline-gray pagination_btn" and @title="Execute"]')
execute_button.click()
sleep(3)

invoice_elements = driver.find_elements(By.XPATH, '//td[@scope="row" and @data-title="Invoice number"]/a')

for i in invoice_elements:
    try:
        i.click()
        sleep(2)
        try:
            # Switch to the popup window
            popup_window = driver.window_handles[-1]
            driver.switch_to.window(popup_window)

            # Extract invoice number
            invoice_number = driver.find_element(By.XPATH, '//div[@class="total"]/b').text

            # Locate the table and extract rows
            table = driver.find_element(By.XPATH, '//table[@class="table table_style_ipad mb-2"]')
            rows = table.find_elements(By.XPATH, './/tr')

            date = None
            amount = None
            seller = None

            # Extract required data from the rows
            for row in rows:
                if row.find_elements(By.XPATH, './/td[@data-title="Date"]'):
                    date = row.find_element(By.XPATH, './/td[@data-title="Date"]').get_attribute("innerText")
                elif row.find_elements(By.XPATH, './/td[@data-title="Amount"]'):
                    amount = row.find_element(By.XPATH, './/td[@data-title="Amount"]').get_attribute("innerText")
                elif row.find_elements(By.XPATH, './/td[@data-title="Name of seller"]'):
                    seller = row.find_element(By.XPATH, './/td[@data-title="Name of seller"]').get_attribute("innerText")

            # Print the extracted data
            print(f"Invoice No.: {invoice_number}")
            print(f"        Date    : {date}")
            print(f"        Amount  : {amount}")
            print(f"        Seller  : {seller}")

            # Close the popup window and switch back to the main window
            close_button = driver.find_element(By.XPATH, '//a[@role="button" and contains(@class, "close_btn") and @title="Close the window"]')
            close_button.click()
            driver.switch_to.window(driver.window_handles[0])
            driver.execute_script("window.scrollBy(0, 100);")  # Slightly scroll down the page
            sleep(3)
        except Exception as e:
            print(f"Error processing invoice: {e}")
            driver.switch_to.window(driver.window_handles[0])  # Ensure switching back to the main window
    except:
        pass
