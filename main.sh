if [ -n "$NO_GIT_AUTOMATION" ] && [ "$NO_GIT_AUTOMATION" = "YES" ]; then
  echo ========================================== Updating git ==========================================
  git pull
  git reset --hard origin/main
  sleep 5
fi

if [ -n "$NO_PACKAGE_INSTALLED" ] && [ "$NO_PACKAGE_INSTALLED" = "YES" ]; then
  apt-get update && apt-get install -y python3-pip
fi

echo ========================================== Starting ==========================================
python -m pip install -r requirements.txt
python3 main.py


