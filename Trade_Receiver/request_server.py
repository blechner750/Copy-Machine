from flask import Flask, request, jsonify
from selenium import webdriver
import threading
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException

#--- Global Variables ---#
app = Flask(__name__)
driver = None
REFRESH_INTERVAL = 4 * 60 * 60  # Interval 4 hrs
trade_map = {}  # Dictionary to store {MT5_ticket: Web_terminal_ticket}

# Function to start browser and login
def initialize_browser():
    global driver   
    
    # This code will allow you to use Chrome Profile in the browser
    #chrome_options = Options()
    #chrome_options.add_argument("user-data-dir=") # Input User Data Directory
    #chrome_options.add_argument("profile-directory=Default") # Change to the profile you use
    #service = Service("") # Ensure this path is correct
    #driver = webdriver.Chrome(service=service, options=chrome_options)
    #driver.get("")
    
    # Otherwise we launch a window and perform credential input
    driver = webdriver.Chrome() 
    driver.get("")
    driver.implicitly_wait(10)
    perform_login() 
    
    # Make sure menu is open and confirmations turned off
    ensure_trade_menu()
    ensure_trade_confirmations_off()
    
def perform_login():
    try:
        wait = WebDriverWait(driver, 10)
        # Wait for and locate the login fields
        username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
        password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='password-field']")))

        username_field.send_keys("")
        password_field.send_keys("")
        
        login_button = driver.find_element(By.CSS_SELECTOR, ".engine-button--center.engine-button--secondary")
        login_button.click()
        
        # Wait for the user menu to appear as a sign of successful login
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "navbar-UserMenuButton"))
        )
        print("Login successful.")
    except Exception as e:
        print(f"Error during login: {e}") 
 
# Runs a browser refresh, logs in if necessary, and ensures menu and confirmation status 
def refresh_browser():
    try:
        print("Refreshing browser...")
        driver.refresh()
        time.sleep(5)
        
        # Check if login is required by looking for the login field.
        # If the list is non-empty, login fields are present.
        login_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='email']")
        if login_fields:
            print("Login fields detected; performing login.")
            perform_login()
        else:
            print("Login not required; already logged in.")
        
        # Confirm the browser is operational by waiting for the user menu button.
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "navbar-UserMenuButton"))
        )
        ensure_trade_menu()
        ensure_trade_confirmations_off()
        print("Browser refreshed and operational.")
    except Exception as e:
        print(f"Error refreshing browser: {e}")

# Checks browser status by looking for User Menu Button
def is_browser_operational():
    try:
        # Use a short wait to confirm the element is present
        user_menu_button = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "navbar-UserMenuButton"))
        )
        return user_menu_button.is_displayed()
    except Exception as e:
        print(f"Browser operational check failed: {e}")
        return False        

# Opens Trade Menu       
def ensure_trade_menu():
    # Look for elements with the ID "MarketWatch-NewOrder"
    new_order_buttons = driver.find_elements(By.ID, "MarketWatch-NewOrder")
    
    # If at least one is found and it is visible, the trade menu is closed.
    if new_order_buttons and new_order_buttons[0].is_displayed():
        print("Trade menu is not open. Reopening...")
        openTradeMenu() 
    else:
        print("Trade menu is already open.")

# Helper to expose Trade Menu buttons    
def openTradeMenu():  
    click_trade_button()
    click_sl_toggler()
    click_tp_toggler()

# Function to make sure we have set Trade Confirmations off
def ensure_trade_confirmations_off():
    try:
        wait = WebDriverWait(driver, 2)
        actions = ActionChains(driver)

        # Step 1: Hover over or click the user menu button
        user_menu_button = wait.until(EC.presence_of_element_located((By.ID, "navbar-UserMenuButton")))
        actions.move_to_element(user_menu_button).perform()  # Hover to trigger menu
        user_menu_button.click()  # Click to be extra sure

        # Step 2: Click "User settings"
        settings_button = wait.until(EC.element_to_be_clickable((By.ID, "userMenu-UserSettingsButton")))
        settings_button.click()

        # Step 3: Ensure "Turn off trade confirmations" is checked
        trade_confirm_label = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Turn off trade confirmations')]")))

        # Find the input checkbox by the 'for' attribute that corresponds to the label's 'id'
        checkbox = driver.find_element(By.XPATH, f"//input[@type='checkbox' and @id='{trade_confirm_label.get_attribute('for')}']")

        # Check the value attribute to determine if it's checked
        checkbox_value = checkbox.get_attribute("value")
        if checkbox_value.lower() != "true":
            actions.move_to_element(checkbox).click().perform()
            print("Trade confirmations disabled.")
        else:
            print("Trade confirmations were already disabled.")

        # Step 4: Click close button
        close_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'engine-dialog-header__icon-button')]")))
        close_button.click()

    except TimeoutException:
        print("Failed to locate an element in the settings menu.")

# Master Trade Function, to input values and click trade button
def click_trade(data):
    try:
        ensure_trade_menu() # just be certain
        
        direction = data.get("direction", "").upper()  # Ensure uppercase ("BUY" or "SELL")
        mt5_ticket = data['ticket']

        # Identify the correct button based on trade direction
        if direction == "BUY":
            button_selector = '[data-testid="button-buy"]'
        elif direction == "SELL":
            button_selector = '[data-testid="button-sell"]'
        else:
            print(f"Invalid trade direction: {direction}")
            return {"error": "Invalid trade direction"}

        # Wait for the button to be clickable and click it
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
        )
        ActionChains(driver).move_to_element(button).click().perform()
        print(f"Successfully clicked {direction} button.")

        # Attempt to retrieve open trade tickets
        try:
            trade_ids = get_open_trade_ids()
        except Exception as e:
            print(f"Error retrieving open trade IDs: {e}")
            trade_ids = []

        # Look for a new trade ticket that is not already mapped
        new_trade_id = None
        for trade_id in trade_ids:
            if trade_id not in trade_map.values():
                new_trade_id = trade_id
                break

        # If a new ticket is not found, refresh the browser and try again
        if not new_trade_id:
            print("New trade not detected. Refreshing browser and retrying...")
            refresh_browser()
            time.sleep(2)  # Allow time for the table to update

            try:
                trade_ids = get_open_trade_ids()
            except Exception as e:
                print(f"Error retrieving open trade IDs after refresh: {e}")
                trade_ids = []

            for trade_id in trade_ids:
                if trade_id not in trade_map.values():
                    new_trade_id = trade_id
                    break

            # If still no new ticket found, return an error response
            if not new_trade_id:
                return {"error": "Failed to retrieve new trade ticket after browser refresh."}

        # Map the MT5 ticket to the new browser trade ID
        trade_map[mt5_ticket] = new_trade_id
        print(f"Mapped MT5 ticket {mt5_ticket} to browser trade ID {new_trade_id}")

        return {"status": "success", "action": direction, "trade_id": new_trade_id}

    except Exception as e:
        print(f"Error clicking {direction} button: {e}")
        return {"error": str(e)}

# Opens Trade Menu
def click_trade_button():
    trade_button = driver.find_element(By.ID, "MarketWatch-NewOrder")
    trade_button.click()

# Opens SL Input    
def click_sl_toggler():
    sl_toggler_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="sl-toggler"] button')
    sl_toggler_button.click()

# Opens TP Input
def click_tp_toggler():
    tp_toggler_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="tp-toggler"] button')
    tp_toggler_button.click()    

# Inputs the volume for the trade        
def input_volume(volume):
    # Locate the volume form control
    volume_parent = WebDriverWait(driver,10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[formcontrolname="volume"]'))
    )
    # Find the input field inside the form control
    volume_input = volume_parent.find_element(By.CSS_SELECTOR, 'input.engine-input-spinner__input')

    # Clear any existing value in the input field
    volume_input.click()
    volume_input.clear() # clear does not seem to work, so run a backspace queue
    for _ in range(10):
        volume_input.send_keys(Keys.BACKSPACE)

    # Input the volume value
    volume_input.send_keys(str(volume))
    

# Inputs the SL for the trade
def input_sl(sl_value):
    # Locate the SL form control
    sl_parent = WebDriverWait(driver,10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[formcontrolname="slPrice"]'))
    )
    # Find the input field inside the form control
    sl_input = sl_parent.find_element(By.CSS_SELECTOR, 'input.engine-input-spinner__input')

    # Clear any existing value in the input field
    sl_input.click()
    sl_input.clear() # clear does not seem to work, so run a backspace queue
    for _ in range(10):
        sl_input.send_keys(Keys.BACKSPACE)

    # Input the SL value
    sl_input.send_keys(str(sl_value))
    

# Inputs the TP for the trade   
def input_tp(tp_value):
    # Locate the TP form control
    tp_parent = WebDriverWait(driver,10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[formcontrolname="tpPrice"]'))
    )
    # Find the input field inside the form control
    tp_input = tp_parent.find_element(By.CSS_SELECTOR, 'input.engine-input-spinner__input')

    # Clear any existing value in the input field
    tp_input.click()
    tp_input.clear() # clear does not seem to work, so run a backspace queue
    for _ in range(10):
        tp_input.send_keys(Keys.BACKSPACE)

    # Input the TP value
    tp_input.send_keys(str(tp_value))
        
# Function to query the Open Position table and retreive trade tickets     
def get_open_trade_ids():
    try:
        # Locate the open positions container
        container = driver.find_element(By.XPATH, "//mtr-open-positions-desktop[contains(@class, 'open-positions-desktop')]")
        # Find the overflow container that holds the trades
        overflow_container = container.find_element(By.CLASS_NAME, "engine-list--overflow")
        
        # Wait until the number of trade elements is greater than the number of mapped trades.
        WebDriverWait(driver, 10).until(
            lambda d: len(overflow_container.find_elements(By.TAG_NAME, "engine-list-element")) > len(trade_map)
        )
        
        # Get all trade elements
        trade_elements = overflow_container.find_elements(By.TAG_NAME, "engine-list-element")
        print(f"Found {len(trade_elements)} trade entries")

        trade_data = []
        for trade in trade_elements:
            try:
                # Locate ticket ID within the trade element (note the correct class with double underscores)
                ticket_element = trade.find_element(By.XPATH, ".//div[contains(@class, 'bottom-section-table__position-id')]")
                ticket_id = ticket_element.text.strip()
                trade_data.append(ticket_id)
            except NoSuchElementException:
                print("Warning: Could not find ticket ID for a trade entry")
        
        return trade_data

    except NoSuchElementException as e:
        print(f"Error: Could not locate trade list container: {e}")
        return []
    except TimeoutException as e:
        print(f"Error: Timeout while waiting for trade elements to load: {e}")
        return []        

# Function that handles Trade Modifications (change of TP or SL)       
def handle_modify(data):
    # First identify what changes need to be performed
    ticket_id = trade_map.get(data['ticket'])
    new_tp = None;
    new_sl = None;
    if(data['take_profit'] != 0.0):
        new_tp = data['take_profit']
    if(data['stop_loss'] != 0.0):
        new_sl = data['stop_loss']
    
    if not ticket_id:
        return f"Error: Ticket ID {data['ticket']} not found in trade map."
    
    try:
        # Locate the open positions container
        container = driver.find_element(By.XPATH, "//mtr-open-positions-desktop[contains(@class, 'open-positions-desktop')]")
        
        # Find the overflow container that holds the trades
        overflow_container = container.find_element(By.CLASS_NAME, "engine-list--overflow")

        # Get all trade elements
        trade_elements = overflow_container.find_elements(By.TAG_NAME, "engine-list-element")
        
        # Find the correct trade row by searching for the ticket ID inside the trade elements
        trade_row = None
        for trade in trade_elements:
            try:
                ticket_element = trade.find_element(By.XPATH, ".//*[contains(@class, 'bottom-section-table__position-id') and contains(text(), '{}')]".format(ticket_id))
                if ticket_element:
                    trade_row = trade
                    break
            except NoSuchElementException:
                continue  # If ticket element is not found in this trade, skip and try next one
        
        if not trade_row:
            return f"Error: Could not find trade row for ticket ID {ticket_id}"

        # Modify TP if needed
        if new_tp is not None:
            edit_tp_button = trade_row.find_element(By.XPATH, ".//mtr-security-order-button[@id='editTakeProfit']//button")
            edit_tp_button.click()

            # Wait for the popup and enter TP value
            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, "//mtr-security-order-popup")))

            tp_input = driver.find_element(By.XPATH, "//mtr-security-order-popup//input[contains(@class, 'engine-input-spinner__input')]")
            tp_input.click()
            tp_input.clear()
            for _ in range(10):
                tp_input.send_keys(Keys.BACKSPACE)

            tp_input.send_keys(str(new_tp))

            # Save TP
            save_button = driver.find_element(By.XPATH, "//mtr-security-order-popup//button[contains(@data-testid, 'save-button')]")
            save_button.click()
            print(f"Updated TP for trade {ticket_id} to {new_tp}")

        # Modify SL if needed
        if new_sl is not None:
            edit_sl_button = trade_row.find_element(By.XPATH, ".//mtr-security-order-button[@id='editStopLoss']//button")
            edit_sl_button.click()

            # Wait for the popup and enter SL value
            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, "//mtr-security-order-popup")))

            sl_input = driver.find_element(By.XPATH, "//mtr-security-order-popup//input[contains(@class, 'engine-input-spinner__input')]")
            sl_input.click()
            sl_input.clear()
            for _ in range(10):
                sl_input.send_keys(Keys.BACKSPACE)
            sl_input.send_keys(str(new_sl))

            # Save SL
            save_button = driver.find_element(By.XPATH, "//mtr-security-order-popup//button[contains(@data-testid, 'save-button')]")
            save_button.click()
            print(f"Updated SL for trade {ticket_id} to {new_sl}")

        return f"Successfully updated TP and/or SL for trade {ticket_id}."

    except NoSuchElementException:
        print(f"Error: Could not find trade row for ticket ID {ticket_id}")
        return f"Error: Could not find trade row for ticket ID {ticket_id}"
        
# Function to remove trade from internal dictionary once closed
def handle_delete(data):
    mt5_ticket = data['ticket']
    if mt5_ticket in trade_map:
        del trade_map[mt5_ticket]
        return {"success": f"Trade {mt5_ticket} removed"}
    else:
        return {"error": "Trade ticket not found"}

# Function to open new trade    
def handle_trade(data):
    volume = data['volume']
    stop_loss = data['stop_loss']
    take_profit = data['take_profit']
    input_volume(volume)
    input_sl(stop_loss)
    input_tp(take_profit)
    return click_trade(data)   

# Function that holds logic for the server POST requests
@app.route('/api/trades', methods=['POST'])
def handle_trades():
    try: 
        # Quick check to make sure browser didn't crash
        if not is_browser_operational():
            refresh_browser()
        
        # Attempt to get the JSON data from the request
        data = request.get_json()

        # If data is missing or invalid, respond with a more specific error
        if not data:
            return jsonify({"error": "No JSON data received, or invalid format"}), 400
        
        # Example: Check if all required fields are present
        required_fields = ["action", "ticket", "volume", "direction", "take_profit", "stop_loss"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
        
        # Process the data (just print it for now)
        print(f"Received trade data: {data}")
        action = data['action']
        
        if action == "trade":
            return handle_trade(data)
        elif action == "modify":
            return handle_modify(data)
        elif action == "delete":
            return handle_delete(data)
        else:
            return jsonify({"error": "Invalid action"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Launchs the server and initialzes browser
if __name__ == '__main__':
    initialize_browser()
    app.run(host="0.0.0.0", port=5000)