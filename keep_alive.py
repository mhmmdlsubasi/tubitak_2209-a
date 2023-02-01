import os
from flask import Flask, send_file, render_template
from zipfile import ZipFile
from threading import Thread

app = Flask("")
@app.route('/')
def home():
    directory = 'work/'
    files = os.listdir(directory)
    return render_template('index.html', files=files)

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
    app.run(debug=True) # host="0.0.0.0", port=530

def keep_alive():
    t = Thread(target=run)
    t.start()
