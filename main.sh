python -m pip install -r requirements.txt
if [ -n "$NO_GIT_AUTOMATION" ] && [ "$NO_GIT_AUTOMATION" = "YES" ]; then
  echo ========================================== Updating git ==========================================
  git pull
  git reset --hard origin/main
  sleep 5
  echo ========================================== Starting ==========================================
  python3 main.py
else
  echo ========================================== Starting ==========================================
  python3 main.py
fi
