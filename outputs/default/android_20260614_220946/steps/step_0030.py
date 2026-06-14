driver.click_text("Silent")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))