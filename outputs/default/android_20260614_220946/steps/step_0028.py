driver.click_resource_id("com.google.android.deskclock:id/collapsing_toolbar_layout")
driver.wait_idle(1)
print(driver.current_app())
print(driver.snapshot_text(max_chars=3000))