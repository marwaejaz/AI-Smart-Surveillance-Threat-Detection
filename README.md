# AI Smart Surveillance & Threat Detection System

A real-time surveillance application built in Python that uses a YOLOv8 object-detection model on a live webcam feed to identify people and potentially dangerous objects, track suspicious behavior over time, monitor restricted zones, and raise instant alerts across multiple channels.

Originally built as a group project (Batch 1), then independently extended across an 8-week Advanced Batch internship with SoftaVerse Tech House, adding analytics, search, role-based access, real-time push notifications, and testing/optimization passes.

---

## Features

- **Real-time object detection** — YOLOv8-based detection of people and objects from a live webcam feed.
- **Weapon detection** — flags dangerous objects (knives, guns, etc.) with instant multi-channel alerts.
- **Suspicious behavior tracking** — centroid-based tracking flags a person loitering in place beyond a configurable time threshold.
- **Crowd detection** — alerts when the number of detected people exceeds a configurable limit.
- **Restricted zone monitoring** — draw custom zones on the live feed; get alerted the moment they're breached.
- **Multi-channel alerting** — on-screen notifications, sound alerts, optional text-to-speech, email, and real-time Discord push notifications.
- **Persistent event logging** — every alert is stored in a local SQLite database.
- **Analytics dashboard** — summary stats and a 7-day event trend chart, built from real logged data.
- **Searchable incident log** — filter and search your entire alert history by keyword or type.
- **Role-based access control** — separate Admin (full control) and Viewer (read-only) logins.
- **Night mode, heatmap overlay, and dual-camera support.**

## Tech Stack

| Component | Technology |
|---|---|
| Object detection | YOLOv8 (Ultralytics), OpenCV |
| Interface | Tkinter, Pillow (PIL) |
| Data storage | SQLite |
| Real-time notifications | Discord Webhook API, SMTP (email) |
| Optional audio | pygame / pyttsx3 (text-to-speech) |
| Config / secrets | python-dotenv |

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/marwaejaz/AI-Smart-Surveillance-Threat-Detection.git
   cd AI-Smart-Surveillance-Threat-Detection
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your environment file**

   Create a file named `.env` in the project root (this file is never committed to the repository, since it holds your secrets) with the following:
   ```
   ADMIN_PASSWORD=your_admin_password
   VIEWER_PASSWORD=your_viewer_password
   DISCORD_WEBHOOK_URL=your_discord_webhook_url
   SENDER_EMAIL=your_email@example.com
   SENDER_PASSWORD=your_email_app_password
   RECIEVER_EMAIL=recipient_email@example.com
   ```
   Only `ADMIN_PASSWORD` is strictly required to log in — the rest enable optional features (Discord alerts, email alerts) and can be left out if you don't need them.

4. **Run the application**
   ```bash
   python main.py
   ```

## Usage

1. Launch the app and log in with your Admin or Viewer password.
2. Click **START** to begin the live camera feed and detection.
3. Click **Draw Zone** to mark a restricted area directly on the video feed.
4. Use **Analytics** to view summary statistics and trends.
5. Use **Search Log** to look up past incidents by keyword or type.
6. Adjust detection sensitivity, crowd limit, and other settings from the Quick Settings panel, then click **Apply**.

**Admin vs. Viewer:** Admin accounts have full control (camera, zones, settings). Viewer accounts can monitor the live feed, stats, analytics, and search log, but cannot change zones, settings, or camera state.

## Known Limitations

- The object-detection model is general-purpose (trained on the COCO dataset), not weapon-specific, so it can occasionally misclassify visually similar objects (e.g. a pencil as a knife).
- A minor UI layout issue exists where the dashboard's right-side panel can visually shift shortly after the camera starts on some displays with non-standard Windows scaling settings; this does not affect detection, logging, or alerting functionality.

## Security

No passwords, API keys, or webhook URLs are stored in source code — all secrets are loaded from a local `.env` file, which is excluded from version control.

## Contributors

Marwa Ejaz — BS Artificial Intelligence, FUUAST Islamabad Campus
