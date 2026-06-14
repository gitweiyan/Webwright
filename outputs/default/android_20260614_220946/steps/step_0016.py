driver.click_resource_id("com.google.android.deskclock:id/sound_image_selected")
driver.wait_idle(1)
print(driver.snapshot_text(max_chars=4000))