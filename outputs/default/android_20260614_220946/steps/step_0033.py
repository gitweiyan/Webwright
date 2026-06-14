driver.click_xpath('//*[@resource-id="com.google.android.deskclock:id/ringtone_primary_text" and @text="BeeBeep Alarm"]')
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))