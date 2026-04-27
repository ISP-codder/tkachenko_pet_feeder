import requests

# Set Cam IP address
cam_ip = '192.168.1.138:8080'

url = f'http://{cam_ip}/'
message = 'TEST'

response = requests.post(url, data={'message': message})
print(response.text)