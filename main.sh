echo ========================================== Updating git ==========================================
git pull
git reset --hard origin/main
sleep 5
echo ========================================== Starting ==========================================
chmod 777 /home/runner/utils-bot/venv/lib/python3.10/site-packages/playwright/driver/playwright.sh
chmod 777 /home/runner/utils-bot/venv/lib/python3.10/site-packages/playwright/driver/node
python3 main.py