import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

app_pass = 'nzhsifueiffygcit' 

from_addr = "garyjeffersii@gmail.com"
to_addr = "garyjeffersii@gmail.com"
msg = MIMEMultipart()
msg['From'] = from_addr
msg['To'] = to_addr
msg['Subject'] = "Backups"
body = "swedish horses"
msg.attach(MIMEText(body, 'plain'))
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login(from_addr, app_pass)
text = msg.as_string()
server.sendmail(from_addr, to_addr, text)
server.quit()