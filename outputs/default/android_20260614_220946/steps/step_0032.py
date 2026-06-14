driver.click_xpath('//*[@text="BeeBeep Alarm" and @class="android.widget.TextView"]')
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))