driver.click_xpath('//*[@text="BeeBeep Alarm"]')
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))