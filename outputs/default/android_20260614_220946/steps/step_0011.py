driver.click_resource_id("com.google.android.deskclock:id/day_button_6")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))