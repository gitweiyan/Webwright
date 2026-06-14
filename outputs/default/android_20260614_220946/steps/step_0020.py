driver.click_desc("Navigate up")
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=4000))