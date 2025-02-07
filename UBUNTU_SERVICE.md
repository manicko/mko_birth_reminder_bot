## Setting Up a Systemd Service for Telegram Bot

Below version of systemd service file uses the Python interpreter 
from your virtual environment rather than the system-wide Python. 
This way, you don't need to run a separate command to activate 
the virtual environment before starting the bot.

-
## Steps to Apply the Service File

1. **Copy the service file: [mko_birth_reminder_bot.service](mko_birth_reminder_bot.service).
to the correct location:**

   ```bash
   sudo cp mko_birth_reminder_bot.service /etc/systemd/system/
   ```

2. **Make sure to update the fields in the file:**
`WorkingDirectory`, `User`, and `Group`


3. **Reload the systemd daemon:**

   ```bash
   sudo systemctl daemon-reload
   ```

4. **Enable the service to start at boot:**

   ```bash
   sudo systemctl enable mko_birth_reminder_bot.service
   ```

4. **Start the service:**

   ```bash
   sudo systemctl start mko_birth_reminder_bot.service
   ```

5. **Check the service status:**

   ```bash
   sudo systemctl status mko_birth_reminder_bot.service
   ```

With these changes, your service will automatically use the virtual environment without needing to manually activate it.

### Should you see the following error:
   ```bash
   status=217/USER
   ```
It means that the user or user group is not properly configured.
Check the 2. point of this readme.