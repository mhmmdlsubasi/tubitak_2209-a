from flask import Flask, send_file, render_template, request
from datetime import datetime, timedelta
from pytz import timezone
import threading
#from function import instant
import sqlite3
import os

def timezoneConverter(utc_datetime):
    return utc_datetime.astimezone(timezone('Turkey'))

app = Flask("")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dataset')
def index():
	dict1 = {}
	for il in os.listdir("work/"):
		dict1.setdefault(il, [])
		for ilce in os.listdir(f"work/{il}/"):
			dict1[il].append(ilce)
	return render_template('dataset.html', cities=dict1)

@app.route('/data', methods=['POST'])
def data():
	start_time = request.form['start_time']
	end_time = request.form['end_time']
	il = request.form['il']
	ilce = request.form['ilce']

	start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
	end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

	dir = f"work/{il}/{ilce}/"
	# SQLite veritabanından verileri çekin
	conn = sqlite3.connect(dir + 'data.db')
	cursor = conn.cursor()
	command = f"""SELECT datetime(veriZamani), sicaklik, nem, yagis00Now, ruzgarYon, ruzgarHiz, denizeIndirgenmisBasinc FROM instantData WHERE (datetime(veriZamani) BETWEEN '{start_time}' AND '{end_time}') """  # AND (Saat BETWEEN '{start_saat}' AND '{end_saat}')
	cursor.execute(command)
	data = cursor.fetchall()
	conn.close()

	# instant(il, ilce).graph(dir, data)

	# return send_file(dir+"user/meteogram.pdf", as_attachment=True)
	return data

@app.route('/<path:file_path>')
def download_file(file_path):
	if os.path.isfile(file_path): 
		return send_file(file_path, as_attachment=True)
	if os.path.isdir(file_path):
		files=os.listdir(file_path)
		dict1={}
		for file in files:
			tarih = os.stat(file_path+"/"+file).st_mtime
			tarih_format = format(timezoneConverter(datetime.fromtimestamp(tarih)), "%d/%m/%Y %H:%M:%S")
			boyut = os.stat(file_path+"/"+file).st_size

			if boyut<1024:
				boyut_format = f"{round(boyut,1)} B"
			elif boyut<1024*1024:
				boyut_format = f"{round(boyut/1024,1)} kB"
			elif boyut<1024*1024*1024:
				boyut_format = f"{round(boyut/(1024*1024),1)} MB"
			elif boyut<1024*1024*1024*1024:
				boyut_format = f"{round(boyut/(1024*1024*1024),1)} GB"
			
			if os.path.isfile(file_path+"/"+file):
				file_type = 0
			elif os.path.isdir(file_path+"/"+file):
				file_type = 1
			
			dict1.setdefault(file, [tarih, tarih_format, boyut, boyut_format, file_type])
		return render_template('download.html', dict1=dict1, file_path=file_path)
	else:
		return "File or directory not found."

def run():
    app.run() # host="0.0.0.0", port=8080

def keep_alive():
	t = threading.Thread(target=run)
	t.start()