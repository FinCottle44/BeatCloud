from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
import csv, time
test_data = []

with open('test.csv') as f:
  reader = csv.DictReader(f)
  for row in reader:
    test_data.append(row)
options = webdriver.ChromeOptions()
options.add_argument('ignore-certificate-errors')
options.set_capability("acceptInsecureCerts", True)

driver = webdriver.Chrome(options=options)

driver.get("https://localhost/dev")
# Wait for visualizer to load
WebDriverWait(driver, 5).until(
    EC.presence_of_element_located((By.ID, "btn_link_create"))
)

create_button = driver.find_element(By.ID,('btn_link_create'))
create_button.click() 

# # Wait for visualizer to load
# WebDriverWait(driver, 10).until(
#     EC.presence_of_element_located((By.ID, "visualizer"))
# )



# for test in test_data:
#   # Navigate to page
  
#   # Set test case values
#   if test['disp_title'] == 'Y': 
#     driver.find_element_by_id('title').send_keys('My Title')

#   # etc for other fields
  
#   # Run test
#   driver.find_element_by_id('runTest').click() 
  
#   # Assertions
#   assert driver.title == 'Expected Title'

# driver.quit()