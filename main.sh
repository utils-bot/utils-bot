if [ "$NO_GIT_AUTOMATION" = "YES" ]; then
    echo ========================================== Updating git ==========================================
    git pull
    git reset --hard origin/main
fi

if [ "$NO_PIP_INSTALLED" = "YES" ]; then
    echo ========================================== Installing dependencies ==========================================
    apt-get update && apt-get install -y python3-pip
fi

echo ========================================== Starting ==========================================
python main.py
