## Command to deploy in raspberrypi
```bash
cd /var/www/
rm -rf html
cp -r /home/pi/krishna/cropicco-ui/html/ /var/www/html
reboot
```

## Command to take Build of the project
```bash
$env:NODE_OPTIONS="--openssl-legacy-provider"
npx ng build --configuration production
```

## Command to run project Locally
```bash
npm start
```
or
```bash
cropicco-ui@0.0.0 start
set NODE_OPTIONS=--openssl-legacy-provider && ng serve
```
