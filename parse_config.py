import json

datetime_current = "2016-12-19 10:23"

with open('./lokomachine/export/config/config_discount.json') as data_file:
    data = json.loads(data_file.read())

print data
