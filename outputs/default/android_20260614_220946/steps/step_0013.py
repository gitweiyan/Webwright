driver.click_text("Dismiss")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))