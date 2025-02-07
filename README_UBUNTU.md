## For Ubuntu
You can install Python 3.12 in a virtual environment (`venv`) for a specific user while keeping Python 3.10 as the system's default version. Here’s a step-by-step guide:

### 1. **Install Dependencies**
Update the package list and install dependencies:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y software-properties-common build-essential libssl-dev libffi-dev python3-dev
```

### 2. **Add the PPA Repository for Python 3.12**
Ubuntu 22.04 uses Python 3.10 by default, but you can add the `deadsnakes` repository:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
```

### 3. **Install Python 3.12**
Now, install Python:

```bash
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

### 4. **Create a Virtual Environment with Python 3.12**
Now, let's create a virtual environment for a specific user.

### 4.1 Switch to the User (if needed)
If you need to set up the environment for another user, switch to them:

```bash
sudo -u username -i
```

### 4.2 Create the Virtual Environment
Create a virtual environment in `~/venvs/myenv`:

```bash
python3.12 -m venv ~/venvs/myenv
```

### 4.3 Activate the Virtual Environment
```bash
source ~/venvs/myenv/bin/activate
```

Now, Python 3.12 is used inside the environment, while Python 3.10 remains the system's default version.

### 5. **Verify Installation**
```bash
python --version
```
Expected output:
```
Python 3.12.x
```

### 6. **Deactivate the Virtual Environment**
To exit the virtual environment, simply run:

```bash
deactivate
```

After this, the system's default Python 3.10 will be used again.

Now you can install packages in this virtual environment without 
affecting the system-wide Python version. 🚀

To launch the bot as a service so it restart if system reboot please [read](UBUNTU_SERVICE.md).