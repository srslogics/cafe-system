import qrcode

url = "https://cafe-system-z4fx.onrender.com/table/1"

img = qrcode.make(url)

img.save("table1_qr.png")