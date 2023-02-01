from flask import Flask, send_file, render_template, request
from datetime import datetime
import threading
#import function
import sqlite3
import os

app = Flask("")


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dataset')
def index():
	il = ["Samsun", "Amasya", "Ordu", "Sinop", "İstanbul", "Kahramanmaraş", "Osmaniye","Rize"]
	ilce = ["Atakum", "Merkez", "Arnavutköy", "Elbistan", "Altınordu"]
	#district = instant(None, None).district
	return render_template('dataset.html', il=il, ilce=ilce)

@app.route('/data', methods=['POST'])
def data():
	start_time = request.form['start_time']
	end_time = request.form['end_time']
	il = request.form['il']
	ilce = request.form['ilce']

	start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
	end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

	start_tarih = format(start_time, "%d/%m/%Y")
	start_saat = format(start_time, "%H:%M:%S")

	end_tarih = format(end_time, "%d/%m/%Y")
	end_saat = format(end_time, "%H:%M:%S")

	dir = f"work/{il}/{ilce}/"
	# SQLite veritabanından verileri çekin
	conn = sqlite3.connect(dir + 'data.db')
	cursor = conn.cursor()
	command = f"""SELECT Tarih, Saat, Sıcaklık, Nem, YağışMiktarı, RüzgarYönü, RüzgarHızı, DİBasınç FROM instantData WHERE (Tarih BETWEEN '{start_tarih}' AND '{end_tarih}') """  # AND (Saat BETWEEN '{start_saat}' AND '{end_saat}')
	cursor.execute(command)
	data = cursor.fetchall()
	conn.close()

	#function.instant(il, ilce).graph(dir, data)

	#return send_file(dir+"/user/meteogram.pdf", as_attachment=True)
	return data

@app.route('/download/<path:file_path>')
def download_file(file_path):
    if os.path.isfile(file_path): 
        return send_file(file_path, as_attachment=True)
    elif os.path.isdir(file_path):
        files=os.listdir(file_path)
        size={}
        for file in files:
            size.setdefault(file, os.stat(file_path+"/"+file).st_size)

        return render_template('download.html', files=size, file_path=file_path)
    #elif os.path.isdir(file_path):
        #zip_file_name = file_path + ".zip"
        #with ZipFile(zip_file_name, 'w') as zip:
            #for root, dirs, files in os.walk(file_path):
                #for file in files:
                    #zip.write(os.path.join(root, file))
        #return send_file(zip_file_name, as_attachment=True)
    else:
        return "File or directory not found."

def run():
    app.run(host="0.0.0.0", port=8080) # host="0.0.0.0", port=530

def keep_alive():
    t = threading.Thread(target=run)
    t.start()
