import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

app_pass = 'nzhsifueiffygcit' 

fromaddr = "garyjeffersii@gmail.com"
toaddr = "garyjeffersii@gmail.com"
msg = MIMEMultipart()
msg['From'] = fromaddr
msg['To'] = toaddr
msg['Subject'] = "Backups"
body = "swedish horses"
msg.attach(MIMEText(body, 'plain'))
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login(fromaddr, app_pass)
text = msg.as_string()
server.sendmail(fromaddr, toaddr, text)
server.quit()