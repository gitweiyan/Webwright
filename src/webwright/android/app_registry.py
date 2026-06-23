# Copyright 2026 The android_world Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""App name to ADB activity mappings for open_app actions."""

import re
from typing import Optional

# pylint: disable=line-too-long
_PATTERN_TO_ACTIVITY = {
    'google chrome|chrome': (
        'com.android.chrome/com.google.android.apps.chrome.Main'
    ),
    'google chat': (
        'com.google.android.apps.dynamite/com.google.android.apps.dynamite.startup.StartUpActivity'
    ),
    'settings|system settings': 'com.android.settings/.Settings',
    'youtube|yt': (
        'com.google.android.youtube/com.google.android.apps.youtube.app.WatchWhileActivity'
    ),
    'google play|play store|gps': (
        'com.android.vending/com.google.android.finsky.activities.MainActivity'
    ),
    'gmail|gemail|google mail|google email|google mail client': (
        'com.google.android.gm/.ConversationListActivityGmail'
    ),
    'google maps|gmaps|maps|google map': (
        'com.google.android.apps.maps/com.google.android.maps.MapsActivity'
    ),
    'google photos|gphotos|photos|google photo|google pics|google images': (
        'com.google.android.apps.photos/com.google.android.apps.photos.home.HomeActivity'
    ),
    'google calendar|gcal': (
        'com.google.android.calendar/com.android.calendar.AllInOneActivity'
    ),
    'camera': 'com.android.camera2/com.android.camera.CameraLauncher',
    'audio recorder': (
        'com.dimowner.audiorecorder/com.dimowner.audiorecorder.app.welcome.WelcomeActivity'
    ),
    'google drive|gdrive|drive': (
        'com.google.android.apps.docs/.drive.startup.StartupActivity'
    ),
    'google keep|gkeep|keep': (
        'com.google.android.keep/.activities.BrowseActivity'
    ),
    'grubhub': (
        'com.grubhub.android/com.grubhub.dinerapp.android.splash.SplashActivity'
    ),
    'tripadvisor': (
        'com.tripadvisor.tripadvisor/com.tripadvisor.android.ui.launcher.LauncherActivity'
    ),
    'starbucks': 'com.starbucks.mobilecard/.main.activity.LandingPageActivity',
    'google docs|gdocs|docs': (
        'com.google.android.apps.docs.editors.docs/com.google.android.apps.docs.editors.homescreen.HomescreenActivity'
    ),
    'google sheets|gsheets|sheets': (
        'com.google.android.apps.docs.editors.sheets/com.google.android.apps.docs.editors.homescreen.HomescreenActivity'
    ),
    'google slides|gslides|slides': (
        'com.google.android.apps.docs.editors.slides/com.google.android.apps.docs.editors.homescreen.HomescreenActivity'
    ),
    'google voice|voice': (
        'com.google.android.apps.googlevoice/com.google.android.apps.googlevoice.SplashActivity'
    ),
    'clock': 'com.google.android.deskclock/com.android.deskclock.DeskClock',
    'google search|google': (
        'com.google.android.googlequicksearchbox/com.google.android.googlequicksearchbox.SearchActivity'
    ),
    'contacts': (
        'com.google.android.contacts/com.android.contacts.activities.PeopleActivity'
    ),
    'facebook|fb': 'com.facebook.katana/com.facebook.katana.LoginActivity',
    'whatsapp|wa': 'com.whatsapp/com.whatsapp.Main',
    'instagram|ig': (
        'com.instagram.android/com.instagram.mainactivity.MainActivity'
    ),
    'twitter|tweet': 'com.twitter.android/com.twitter.app.main.MainActivity',
    'snapchat|sc': 'com.snapchat.android/com.snap.mushroom.MainActivity',
    'telegram|tg': 'org.telegram.messenger/org.telegram.ui.LaunchActivity',
    'linkedin': (
        'com.linkedin.android/com.linkedin.android.authenticator.LaunchActivity'
    ),
    'spotify|spot': 'com.spotify.music/com.spotify.music.MainActivity',
    'netflix': (
        'com.netflix.mediaclient/com.netflix.mediaclient.ui.launch.UIWebViewActivity'
    ),
    'amazon shopping|amazon|amzn': (
        'com.amazon.mShop.android.shopping/com.amazon.mShop.home.HomeActivity'
    ),
    'tiktok|tt': (
        'com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.SplashActivity'
    ),
    'discord': 'com.discord/com.discord.app.AppActivity$Main',
    'reddit': 'com.reddit.frontpage/com.reddit.frontpage.MainActivity',
    'pinterest': 'com.pinterest/com.pinterest.activity.PinterestActivity',
    'android world': 'com.example.androidworld/.MainActivity',
    'files': (
        'com.google.android.documentsui/com.android.documentsui.files.FilesActivity'
    ),
    'markor': 'net.gsantner.markor/net.gsantner.markor.activity.MainActivity',
    'clipper': 'ca.zgrs.clipper/ca.zgrs.clipper.Main',
    'messages': (
        'com.google.android.apps.messaging/com.google.android.apps.messaging.ui.ConversationListActivity'
    ),
    'simple sms messenger|simple sms': (
        'com.simplemobiletools.smsmessenger/com.simplemobiletools.smsmessenger.activities.MainActivity'
    ),
    'dialer|phone': (
        'com.google.android.dialer/com.google.android.dialer.extensions.GoogleDialtactsActivity'
    ),
    'simple calendar pro|simple calendar': (
        'com.simplemobiletools.calendar.pro/com.simplemobiletools.calendar.pro.activities.MainActivity'
    ),
    'simple gallery pro|simple gallery': (
        'com.simplemobiletools.gallery.pro/com.simplemobiletools.gallery.pro.activities.MainActivity'
    ),
    'miniwob': (
        'com.google.androidenv.miniwob/com.google.androidenv.miniwob.app.MainActivity'
    ),
    'simple draw pro': (
        'com.simplemobiletools.draw.pro/com.simplemobiletools.draw.pro.activities.MainActivity'
    ),
    'pro expense|pro expense app': (
        'com.arduia.expense/com.arduia.expense.ui.MainActivity'
    ),
    'broccoli|broccoli app|broccoli recipe app|recipe app': (
        'com.flauschcode.broccoli/com.flauschcode.broccoli.MainActivity'
    ),
    'caa|caa test|context aware access': (
        'com.google.ccc.hosted.contextawareaccess.thirdpartyapp/.ChooserActivity'
    ),
    'osmand': 'net.osmand/net.osmand.plus.activities.MapActivity',
    'tasks|tasks app|tasks.org:': (
        'org.tasks/com.todoroo.astrid.activity.MainActivity'
    ),
    'open tracks sports tracker|activity tracker|open tracks|opentracks': (
        'de.dennisguse.opentracks/de.dennisguse.opentracks.TrackListActivity'
    ),
    'joplin|joplin app': 'net.cozic.joplin/.MainActivity',
    'vlc|vlc app|vlc player': 'org.videolan.vlc/.gui.MainActivity',
    'retro music|retro|retro player': (
        'code.name.monkey.retromusic/.activities.MainActivity'
    ),
}
# pylint: enable=line-too-long


def get_adb_activity(app_name: str) -> Optional[str]:
  """Map a human-readable app name to an ADB activity string."""
  for pattern, activity in _PATTERN_TO_ACTIVITY.items():
    if re.match(pattern.lower(), app_name.lower()):
      return activity
  return None
