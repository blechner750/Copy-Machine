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
# Global flag to indicate if a trade action is in progress
ACTION_IN_PROGRESS = False

# Refresh interval: 20 minutes in seconds.
REFRESH_INTERVAL = 20 * 60  # 1200 seconds
trade_map = {}  # Dictionary to store {MT5_ticket: Web_terminal_ticket}

# Function to start browser and login
def initialize_browser():
    global driver   
    
    # This code will allow you to use Chrome Profile in the browser
    chrome_options = Options()
    chrome_options.add_argument("user-data-dir=") # Input User Data Directory
    chrome_options.add_argument("profile-directory=Default") # Change to the profile you use
    service = Service("") # Ensure this path is correct
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("")
    
    # Otherwise we launch a window and perform credential input
    #driver = webdriver.Chrome() 
    #driver.get("")
    #driver.implicitly_wait(10)
    #perform_login() 
    
    # Make sure menu is open and confirmations turned off
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
        print("[perform_login] Login successful.")
    except Exception as e:
        print(f"[perform_login] Error: {e}") 
            
def refresh_browser():
    try:
        print("[refresh_browser] Refresh started")
        driver.refresh()
        time.sleep(5)
        
        # Check if login is required by looking for the login field.
        # If the list is non-empty, login fields are present.
        login_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='email']")
        if login_fields:
            print("[refresh_browser] Login fields detected; performing login.")
            perform_login()
        
        # Confirm the browser is operational by waiting for the user menu button.
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "navbar-UserMenuButton"))
        )
        print("[refresh_browser] Browser refreshed and operational")
    except Exception as e:
        print(f"[refresh_browser] Error refreshing browser: {e}")

def is_browser_operational():
    try:
        # Use a short wait to confirm the element is present
        user_menu_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "navbar-UserMenuButton"))
        )
        return user_menu_button.is_displayed()
    except Exception as e:
        print(f"[is_browser_operational] Error: {e}")
        return False        

# Opens Trade Menu       
def ensure_trade_menu():
    try:
        wait = WebDriverWait(driver, 5)
        
        # Check if the button is visible
        new_order_buttons = wait.until(EC.presence_of_all_elements_located((By.ID, "MarketWatch-NewOrder")))
        
        if new_order_buttons and new_order_buttons[0].is_displayed():
            print("[ensure_trade_menu] Trade menu is not open. Reopening...")
            openTradeMenu() 
        else:
            print("[ensure_trade_menu] Trade menu is already open.")

    except Exception as e:
        print(f"[ensure_trade_menu] Error: {e}")
               

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
            print("[ensure_trade_confirmations_off] Trade confirmations disabled.")
        else:
            print("[ensure_trade_confirmations_off] Trade confirmations were already disabled.")

        # Step 4: Click close button
        close_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'engine-dialog-header__icon-button')]")))
        close_button.click()

    except TimeoutException:
        print("[ensure_trade_confirmations_off] Failed to locate an element in the settings menu.")

def click_trade_market(data):
    try:        
        # Locate the volume form control
        volume_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "Market-Watch-VolumeEditField"))
        )

        # Clear any existing value in the input field
        volume_input.click()
        volume_input.clear()
        for i in range(5):
            volume_input.send_keys(Keys.BACKSPACE)
        
        # Input the volume value
        volume_value = str(data['volume'])
        volume_input.send_keys(volume_value)
        
        # Retrieve and validate trade data
        direction = data.get('direction', '').upper()
        mt5_ticket = data.get('ticket')

        # Identify the correct button based on trade direction
        if direction == "BUY":
            button_selector = "MarketWatch-QuickBuy"
        elif direction == "SELL":
            button_selector = "MarketWatch-QuickSell"
        else:
            print(f"[click_trade_market] Invalid trade direction: {direction}")
            return {"error": "Invalid trade direction"}
        
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, button_selector))
        )
        ActionChains(driver).move_to_element(button).click().perform()
        print(f"[click_trade_market] Successfully clicked the {direction} button.")
        
        # Just wait for table to refresh
        time.sleep(1)
       

        # Map the MT5 ticket to the new browser trade ID
        trade_map[mt5_ticket] = new_trade_id
        return {"status": "success", "action": direction, "trade_id": new_trade_id}
        
    except Exception as e:
        print(f"[click_trade_market] Error: {e}")
        return {"error": str(e)}
        
       

def click_trade_tpsl(data):
    try:       
        direction = data.get("direction", "").upper()  # Ensure uppercase ("BUY" or "SELL")
        mt5_ticket = data['ticket']
        
        # Take the snapshot of existing trade IDs
        before_ids = set(get_open_trade_ids())
        #print(f"[click_trade_tpsl] before_ids: {before_ids}")

        # Identify the correct button based on trade direction
        if direction == "BUY":
            button_selector = '[data-testid="button-buy"]'
        elif direction == "SELL":
            button_selector = '[data-testid="button-sell"]'
        else:
            print(f"[click_trade_tpsl] Invalid trade direction: {direction}")
            return {"error": "Invalid trade direction"}  

        # Wait for the button to be clickable and click it
        button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
        )
        ActionChains(driver).move_to_element(button).click().perform()
        print(f"[click_trade_tpsl]Successfully clicked {direction} button.")
        
        click_back_button()
        
        # Now look for the new trade via set-difference
        time.sleep(2)
        new_trade_id = None
        # First pass
        after_ids = set(get_open_trade_ids())
        diff = after_ids - before_ids
        #print(f"[click_trade_tpsl] after_ids: {after_ids}, diff: {diff}")
        # Filter out any already-mapped
        candidates = [tid for tid in diff if tid not in trade_map.values()]
        if candidates:
            new_trade_id = candidates[0]
        else:
            # Retry once after a quick refresh
            print("[click_trade_tpsl] No new trade detected—refreshing and retrying...")
            refresh_browser()
            time.sleep(2)
            after_ids = set(get_open_trade_ids())
            diff = after_ids - before_ids
            #print(f"[click_trade_tpsl] after refresh, after_ids: {after_ids}, diff: {diff}")
            candidates = [tid for tid in diff if tid not in trade_map.values()]
            if candidates:
                new_trade_id = candidates[0]
       
        if not new_trade_id:
            raise Exception("Failed to detect new trade ticket.")

        # Map the MT5 ticket to the new browser trade ID
        trade_map[mt5_ticket] = new_trade_id
        print(f"[click_trade_tpsl] Mapped MT5 ticket {mt5_ticket} to browser trade ID {new_trade_id}")             

        # Ensure the trade menu remains open for subsequent trades
        return {"status": "success", "action": direction, "trade_id": new_trade_id}

    except Exception as e:
        return {"error": str(e)}


def select_symbol(symbol):
    """
    Locate the symbol container using the ID 'cdk-drop-list-0', then look for an engine-list-element 
    whose embedded <span> text matches the given symbol. Click that element to select the symbol.
    
    Parameters:
        symbol (str): The symbol to select (e.g., "EURUSD").
    
    Returns:
        bool: True if the symbol is found and clicked, False otherwise.
    """
    try:
        # Locate the container with the specific id.
        container = driver.find_element(By.ID, "cdk-drop-list-0")

        # Get all engine-list-element objects inside this container.
        symbol_elements = container.find_elements(By.TAG_NAME, "engine-list-element")

        for element in symbol_elements:
            try:
                # Locate the element with the symbol text.
                # Adjust this XPath if needed based on the structure.
                span_elem = element.find_element(By.XPATH, ".//div[contains(@class, 'symbol-element-desktop__text-symbol')]//span")
                element_symbol = span_elem.text.strip()
                #print(f"Found symbol in element: {element_symbol}")
                if element_symbol == symbol:
                    # Click the element using ActionChains to simulate a natural click.
                    ActionChains(driver).move_to_element(element).click().perform()
                    print(f"[select_symbol] Selected symbol: {symbol}")
                    return True
            except Exception as inner_e:
                # If a particular engine-list-element doesn't contain the expected element, skip it.
                print(f"Skipping an element due to: {inner_e}")
                continue

        print(f"[select_symbol] Symbol '{symbol}' not found in the list.")
        return False

    except Exception as e:
        print(f"[select_symbol] Error: {e}")
        return False

def click_back_button():
    try:
        # Wait for the back button (one containing an engine-icon with name "delete") to be clickable.
        back_button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//engine-icon[@name='delete']]"))
        )
        # Click the back button.
        back_button.click()
    except Exception as e:
        print(f"[click_back_button] Error: {e}")

# Opens Trade Menu
def click_trade_button():
    try:
        trade_button = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.ID, "MarketWatch-NewOrder")))
        ActionChains(driver).move_to_element(trade_button).perform()  # Hover to trigger menu
        trade_button.click()  # Click to be extra sure
    except Exception as e:
        print(f"[click_trade_button] Error: {e}")

# Opens SL Input    
def click_sl_toggler():
    try:
        sl_button = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="sl-toggler"] button')))
        ActionChains(driver).move_to_element(sl_button).perform()  # Hover to trigger menu
        sl_button.click()  # Click to be extra sure
    except Exception as e:
        print(f"[click_sl_toggler] Error: {e}")

# Opens TP Input
def click_tp_toggler():
    try:
        tp_button = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tp-toggler"] button')))
        ActionChains(driver).move_to_element(tp_button).perform()  # Hover to trigger menu
        tp_button.click()  # Click to be extra sure
    except Exception as e:
        print(f"[click_tp_toggler] Error: {e}")

# Inputs the volume for the trade        
def input_volume(volume):
    # Locate the volume form control
    volume_parent = WebDriverWait(driver,2).until(
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
    sl_parent = WebDriverWait(driver,2).until(
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
        
        
def get_open_trade_ids():
    """
    Returns a list of ticket IDs currently shown in the open‐positions table.
    
    If there is no open positions container, returns [] immediately.
    If trade_map is nonempty, waits until the table has strictly more rows
    than the number of entries in trade_map (i.e. a new trade).
    """
    try:
        # Temporarily disable implicit wait so find_elements() returns instantly if nothing is there.
        original_timeout = driver.timeouts.implicit_wait
        driver.implicitly_wait(0)
        
        # 1) Look for the open‐positions container; if none, just return empty:
        containers = driver.find_elements(
            By.XPATH,
            "//mtr-open-positions-desktop[contains(@class, 'open-positions-desktop')]"
        )
        if not containers:
            return []
        container = containers[0]

        # 2) Find the overflow container
        overflow = container.find_elements(By.CLASS_NAME, "engine-list--overflow")
        if not overflow:
            return []
        overflow_container = overflow[0]

        # 4) Collect whatever rows do exist right now
        trade_elements = overflow_container.find_elements(By.TAG_NAME, "engine-list-element")
        print(f"[get_open_trade_ids] Found {len(trade_elements)} trade entries")

        ids = []
        for trade in trade_elements:
            try:
                ticket_el = trade.find_element(
                    By.XPATH,
                    ".//div[contains(@class, 'bottom-section-table__position-id')]"
                )
                ids.append(ticket_el.text.strip())
            except NoSuchElementException:
                # skip rows without a ticket element
                continue
        return ids

    except Exception as e:
        print(f"[get_open_trade_ids] Unexpected error in get_open_trade_ids(): {e}")
        return [] 
    finally:
        # Restore whatever implicit-wait you had before
        driver.implicitly_wait(original_timeout)        

def find_trade_row(ticket_id):
    """
    Locates the trade row (engine-list-element) that contains the given ticket_id.
    Returns the trade row element if found, otherwise None.
    """
    try:
        # Locate the open positions container
        container = driver.find_element(By.XPATH, "//mtr-open-positions-desktop[contains(@class, 'open-positions-desktop')]")
        overflow_container = container.find_element(By.CLASS_NAME, "engine-list--overflow")
        trade_elements = overflow_container.find_elements(By.TAG_NAME, "engine-list-element")
        for trade in trade_elements:
            try:
                ticket_element = trade.find_element(
                    By.XPATH, f".//div[contains(@class, 'bottom-section-table__position-id') and contains(text(), '{ticket_id}')]"
                )
                if ticket_element:
                    return trade
            except NoSuchElementException:
                continue
        return None
    except Exception as e:
        print(f"[find_trade_row] Error: {e}")
        return None
        
def get_trade_row(ticket_id):
    """Return a fresh WebElement for the given ticket_id row."""
    row_xpath = (
        f"//engine-list-element[.//div[contains(@class,'bottom-section-table__position-id') "
        f"and normalize-space(text())='{ticket_id}']]"
    )
    return driver.find_element(By.XPATH, row_xpath)
       

def handle_modify(data):
    # Identify new values for TP and SL
    ticket_id = trade_map.get(data['ticket'])
    new_tp = data['take_profit'] if data['take_profit'] != 0.0 else None
    new_sl = data['stop_loss'] if data['stop_loss'] != 0.0 else None

    if not ticket_id:
        return f"Error: Ticket ID {data['ticket']} not found in trade map."

    try:
        # Locate the trade row for the given ticket ID
        trade_row = get_trade_row(ticket_id)
        if not trade_row:
            return f"Error: Could not find trade row for ticket ID {ticket_id}"

        # --- Modify TP if needed ---
        if new_tp is not None:
            edit_tp_button = trade_row.find_element(By.XPATH, ".//mtr-security-order-button[@id='editTakeProfit']//button")
            edit_tp_button.click()

            WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.XPATH, "//mtr-security-order-popup")))
            tp_input = driver.find_element(By.XPATH, "//mtr-security-order-popup//input[contains(@class, 'engine-input-spinner__input')]")
            tp_input.click()
            tp_input.clear()
            for _ in range(10):
                tp_input.send_keys(Keys.BACKSPACE)
            tp_input.send_keys(str(new_tp))

            save_button = driver.find_element(By.XPATH, "//mtr-security-order-popup//button[contains(@data-testid, 'save-button')]")
            save_button.click()
            print(f"Updated TP for trade {ticket_id} to {new_tp}")
            
            WebDriverWait(driver, 3).until(
                EC.invisibility_of_element_located((By.XPATH, "//mtr-security-order-popup"))
            )                             
            
            trade_row = get_trade_row(ticket_id)
            if not trade_row:
                return f"Error: Trade row disappeared after TP modification for ticket ID {ticket_id}"

        # --- Modify SL if needed ---
        if new_sl is not None:
            edit_sl_button = trade_row.find_element(By.XPATH, ".//mtr-security-order-button[@id='editStopLoss']//button")
            edit_sl_button.click()

            WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.XPATH, "//mtr-security-order-popup")))
            sl_input = driver.find_element(By.XPATH, "//mtr-security-order-popup//input[contains(@class, 'engine-input-spinner__input')]")
            sl_input.click()
            sl_input.clear()
            for _ in range(10):
                sl_input.send_keys(Keys.BACKSPACE)
            sl_input.send_keys(str(new_sl))

            save_button = driver.find_element(By.XPATH, "//mtr-security-order-popup//button[contains(@data-testid, 'save-button')]")
            save_button.click()
            print(f"Updated SL for trade {ticket_id} to {new_sl}")

        return f"Successfully updated TP and/or SL for trade {ticket_id}."

    except NoSuchElementException:
        print(f"Error: Could not find an element for ticket ID {ticket_id}")
        return f"Error: Could not find trade row for ticket ID {ticket_id}"
    except TimeoutException:
        print(f"Error: Timeout while modifying trade {ticket_id}")
        return f"Error: Timeout while modifying trade {ticket_id}"

 
# Function to close trade
def handle_delete(data):
    mt5_ticket = data['ticket']
    if mt5_ticket in trade_map:
        ticket_id = trade_map.get(data['ticket'])        
        if not ticket_id:
            return {"error": f"Ticket ID {data['ticket']} not found in trade map."}
        
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
                return remove_from_map(data)
                
            close_button = trade_row.find_element(By.XPATH, ".//button[@id='closePositionButton' and @title='Close position']")
            close_button.click()
            
            del trade_map[mt5_ticket]
            return f"Successfully closed: {ticket_id}."

        except NoSuchElementException:
            print(f"Error: Could not find trade row for ticket ID {ticket_id}")
            return f"Error: Could not find trade row for ticket ID {ticket_id}"        
            return {"success": f"Trade {mt5_ticket} removed"}
    else:
        return {"error": "Trade ticket not found"}
        
        
def close_all_trades(data):
    """
    Attempts to close every open trade in the browser table.
    Returns a dict summarizing successes and failures.
    """
    tickets = get_open_trade_ids()
    results = {
        "status": None,
        "closed": [],
        "failed": {}
    }

    for ticket in tickets:
        try:
            # Re-find the row for this ticket
            row_xpath = (
                f"//engine-list-element[.//div[contains(@class,'bottom-section-table__position-id') "
                f"and normalize-space(text())='{ticket}']]"
            )
            trade_row = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, row_xpath))
            )

            # Click its close button
            close_btn = trade_row.find_element(
                By.XPATH,
                ".//button[@id='closePositionButton' and @title='Close position']"
            )
            close_btn.click()

            # Wait until that row disappears
            WebDriverWait(driver, 3).until(
                EC.staleness_of(trade_row)
            )

            results["closed"].append(ticket)

        except (TimeoutException, NoSuchElementException) as e:
            results["failed"][ticket] = f"Element issue: {e}"
        except StaleElementReferenceException as e:
            results["failed"][ticket] = f"Stale reference: {e}"
        except Exception as e:
            results["failed"][ticket] = f"Unknown error: {e}"

    # Determine overall status
    if not tickets:
        results["status"] = "no_trades_to_close"
    elif not results["failed"]:
        results["status"] = "success"
    elif results["closed"] and results["failed"]:
        results["status"] = "partial_success"
    else:
        results["status"] = "failure"

    return results
        
def remove_from_map(data):
    mt5_ticket = data['ticket']
    if mt5_ticket in trade_map:
        ticket_id = trade_map.get(data['ticket'])        
        if not ticket_id:
            return f"Error: Ticket ID {data['ticket']} not found in trade map."
        
        try:            
            del trade_map[mt5_ticket]
            return f"Trade removed from map: {ticket_id}."

        except NoSuchElementException:
            print(f"Error: Could not find trade row for ticket ID {ticket_id}")
            return f"Error: Could not find trade row for ticket ID {ticket_id}"        
    else:
        return {"error": "Trade ticket not found"}


def periodic_refresh():
    """Periodically refresh the browser every 20 minutes, waiting until no action is in progress."""
    while True:
        time.sleep(REFRESH_INTERVAL)
        # Ensure we are not in the middle of a trade action.
        while ACTION_IN_PROGRESS:
            print("Action in progress. Waiting for safe refresh...")
            time.sleep(5)  # Check every 5 seconds until safe to refresh
        refresh_browser()        

# Function to open new trade    
def handle_trade(data):
    volume = data['volume']
    stop_loss = data['stop_loss']
    take_profit = data['take_profit']
    symbol = data['symbol']
    if(stop_loss == 0.0 and take_profit == 0.0):
        return click_trade_market(data)
    else:
        select_symbol(symbol)
        openTradeMenu()
        input_volume(volume)
        input_sl(stop_loss)
        input_tp(take_profit)
        return click_trade_tpsl(data)   

# Function that holds logic for the server POST requests
@app.route('/api/trades', methods=['POST'])
def handle_trades():
    global ACTION_IN_PROGRESS
    try: 
        ACTION_IN_PROGRESS = True
        # Quick check to make sure browser didn't crash
        if not is_browser_operational():
            refresh_browser()
        
        # Attempt to get the JSON data from the request
        data = request.get_json()

        # If data is missing or invalid, respond with a more specific error
        if not data:
            return jsonify({"error": "No JSON data received, or invalid format"}), 400
        
        # Example: Check if all required fields are present
        required_fields = ["action", "symbol", "ticket", "volume", "direction", "take_profit", "stop_loss"]
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
        elif action == "delete_all":
            return close_all_trades(data)
        else:
            return jsonify({"error": "Invalid action"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    finally:
            ACTION_IN_PROGRESS = False
        
        
 

# Launchs the server and initialzes browser
if __name__ == '__main__':
    initialize_browser()
    refresh_thread = threading.Thread(target=periodic_refresh, daemon=True)
    refresh_thread.start()
    app.run(host="0.0.0.0", port=5000)