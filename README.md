# 🎂 TELEGRAM BIRTH REMINDER BOT

## 🛠️ Description

Telegram bot that sends notifications about upcoming birthdays.

### **Key Features:**
- 📅 **Automated Birthday Reminders** – Receive notifications about upcoming birthdays.
- 📋 **Easy Management** – Add, remove, or modify records via an intuitive bot menu.
- 📂 **CSV Import/Export** – Manage birthday lists with ease.
- ⏰ **Flexible Scheduling** – Set multiple notification days (e.g., 1, 5, 7, or 14 days before).
- 🔧 **Customizable Settings** – Adjust notification timing for each record individually.

---

## ⚙️ Setup

### **1️⃣ Install Dependencies**
- Download the package.
- Set up a virtual environment (Python 3.12 is required).
- Install all required dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### **2️⃣ Initialize the Database**
- Run the following command to set up the SQLite database:
  ```bash
  python mko_birth_reminder_bot/main.py init-db
  ```

### **3️⃣ Export Default Configuration**
- Export the default configuration files to your home directory:
  ```bash
  python mko_birth_reminder_bot/main.py export-config
  ```
  ⚠ **Important:** Save the location of the configuration files.

---

## 🔑 Configuration

### **4️⃣ Configure Telethon API Connection**
- Locate the `secrets.yaml` file in the exported configuration path.
- Set up your **Telethon API** credentials (refer to [Telethon API Docs](https://docs.telethon.dev/)):
  ```yaml
  TELETHON_API:
    bot_token: put_your_bot_token
    client:
      api_hash: put_your_api_hash
      api_id: put_your_api_id
      device_model: your_device_model
      lang_code: lang_code
      session: session
      system_lang_code: system_lang_code
      system_version: system_version
  ```

### **5️⃣ Configure Notification Periods**
- Set how many days in advance the bot should send notifications by editing `config.yaml`:
  ```yaml
  default_notice:
    - 0
    - 1
    - 2
    - 3
    - 5
    - 7
    - 14
  ```
  ⚠ **Changing other settings in `config.yaml` is not recommended. Proceed with caution.**

---

## 🚀 Running the Bot

### **6️⃣ Start the Bot**
- Run the following command to launch the bot:
  ```bash
  python mko_birth_reminder_bot/main.py run-bot
  ```

- Contact the bot via Telegram using its username (starts with `@`) and send the `/start` command to open the menu.

### **7️⃣ Stop the Bot**
- To stop the bot, use the following command:
  ```bash
  pkill -f mko_birth_reminder_bot
  ```

---

## 📢 Notes
- The bot must remain running to send notifications.
- Ensure that your Telegram API credentials are correctly configured.

Happy reminding! 🎉
