

# Step 1
print(driver.current_app())
print(driver.snapshot_text(max_chars=5000))


# Step 2
driver.click_text("Clock")


# Step 3
driver.click_resource_id("com.google.android.deskclock:id/fab")


# Step 4
driver.click_text("Alarm")


# Step 5
driver.click_resource_id("com.google.android.deskclock:id/fab")


# Step 6
driver.click_text("AM")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 7
driver.click_text("8")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 8
driver.click_text("25")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 9
driver.click_text("OK")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 10
driver.click_text("S")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 11
driver.click_resource_id("com.google.android.deskclock:id/day_button_6")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 12
driver.click_text("Default (Cesium)")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 13
driver.click_text("Dismiss")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 14
driver.click_text("BeeBeep Alarm")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 15
driver.click_text("BeeBeep Alarm")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 16
driver.click_resource_id("com.google.android.deskclock:id/sound_image_selected")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 17
driver.click_resource_id("com.google.android.deskclock:id/action_bar_root")
print(driver.snapshot_text(max_chars=4000))


# Step 18
driver.click_resource_id("com.google.android.deskclock:id/action_bar_root").left(className="android.widget.ImageButton").click()


# Step 19
driver.click_resource_id("com.google.android.deskclock:id/toolbar")
driver.click_desc("Navigate up")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))


# Step 20
driver.click_desc("Navigate up")
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=4000))


# Step 21
driver.click_text("Silent")


# Step 22
driver.click_text("BeeBeep Alarm")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))


# Step 23
driver.click_text_contains("BeeBeep Alarm")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))


# Step 24
driver.click_xpath('//*[@text="BeeBeep Alarm"]')
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))


# Step 25
driver.click_resource_id("com.google.android.deskclock:id/sound_image_selected")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))


# Step 26
driver.click_resource_id("com.google.android.deskclock:id/sound_image_selected")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))


# Step 27
driver.click_resource_id("com.google.android.deskclock:id/action_bar_root")
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))


# Step 28
driver.click_resource_id("com.google.android.deskclock:id/collapsing_toolbar_layout")
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))


# Step 29
driver.press('back')
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))


# Step 30
driver.click_text("Silent")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=3000))


# Step 31
driver.click_text("BeeBeep Alarm")
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))


# Step 32
driver.click_xpath('//*[@text="BeeBeep Alarm" and @class="android.widget.TextView"]')
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))


# Step 33
driver.click_xpath('//*[@resource-id="com.google.android.deskclock:id/ringtone_primary_text" and @text="BeeBeep Alarm"]')
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))
