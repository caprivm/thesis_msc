#cloud-config
package_upgrade: true

password: orion
chpasswd: { expire: False }
ssh_pwauth: True

runcmd:
 - [ sh, -c, 'echo "nameserver 8.8.8.8" >> /etc/resolv.conf' ]
 - sudo apt update && sudo apt install -y apache2
 - sudo systemctl restart apache2
 - sudo apt install -y prometheus-node-exporter
 - sudo mkdir -p /var/www/example.com
 - sudo chown -R $USER:$USER /var/www/example.com
 - sudo chmod -R 755 /var/www/example.com
 - sudo echo -e "<html>\n\t<head>\n\t\t<title>Welcome to example.com\!</title>\n\t</head>\n\t<body>\n\t\t<h1>Success\!  The example.com virtual host is working!</h1>\n\t</body>\n</html>" >> /var/www/example.com/index.html
 - sudo sed -i 's/\\//g' /var/www/example.com/html/index.html
 - sudo echo -e "<VirtualHost *:80>\n\tServerAdmin webmaster@localhost\n\tServerName example.com\n\tServerAlias www.example.com\n\tDocumentRoot /var/www/example.com\n\tErrorLog /var/log/apache2/error.log\n\tCustomLog /var/log/apache2/access.log combined\n</VirtualHost>" >> /etc/apache2/sites-available/example.com.conf
 - sudo a2ensite example.com.conf
 - sudo a2dissite 000-default.conf
 - sudo apache2ctl configtest
 - sudo systemctl restart apache2

