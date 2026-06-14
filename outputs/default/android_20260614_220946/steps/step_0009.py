driver.click_text("OK")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))