#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Install Python Enviroment"
sudo apt-get install python-virtualenv python-dev git -y

echo "Install WebServer"
sudo apt-get install nginx supervisor gunicorn -y

echo "Install Database"
sudo apt-get install libpq-dev postgresql postgresql-client postgresql-contrib -y

echo "Install dependencies"
virtualenv env
git clone https://github.com/ehooo/django_mqtt.git
bash django_mqtt/script/install_mosquitto_auth_plugin.sh
env/bin/pip install -r django_mqtt/requirements.txt
mr django_mqtt -fr
env/bin/pip install pip --upgrade
env/bin/pip install -r requirements.txt

echo "
DJANGO_SETTINGS_MODULE=red_casa.settings
DJANGO_WSGI_MODULE=red_casa.wsgi
" >> env/bin/activate

echo "Configure supervisor"
echo "
[program:django_red_casa]
command = $PWD/env/bin/gunicorn test_web.wsgi:application -b 127.0.0.1:8000
directory = $PWD/
user = www-data
autostart = true
autorestart = true
# environment = DJANGO_SETTINGS_MODULE=\"red_casa.settings\",DJANGO_WSGI_MODULE=\"red_casa.wsgi\"
" > supervisor.conf
sudo cp supervisor.conf /etc/supervisor/conf.d/django_red_casa.conf
rm supervisor.conf

echo "Making directories"
mkdir certs
chown www-data certs
env/bin/python manage.py collectstatic

echo "Configure nginx"
echo "server {
    server_name _;

    access_log off;

    location /static/ {
        alias $PWD/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}" > nginx.conf
sudo cp nginx.conf /etc/nginx/sites-available/django_red_casa
sudo ln -s /etc/nginx/sites-available/django_red_casa /etc/nginx/sites-enabled/django_red_casa
sudo rm /etc/nginx/sites-enabled/default
rm nginx.conf

sudo systemctl restart supervisor.service
sudo service nginx restart

echo "Configure Database"
sudo su postgres sh -c "createuser red_casa -P -d"
sudo su postgres sh -c "createdb red_casa"
sudo su postgres sh -c "createdb powerdns"
# sudo runuser -u postgres psql
env/bin/python manage.py syncdb
