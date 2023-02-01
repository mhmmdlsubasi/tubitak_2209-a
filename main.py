from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.dates as mdates
from pytz import timezone
import math as m
import requests
import logging
import sqlite3
import os
from keep_alive import keep_alive

logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

logging.debug('Debug mesajı')
logging.info('Info mesajı')
logging.warning('Warning mesajı')
logging.error('Error mesajı')

rcParams.update({'figure.autolayout': True})

session = requests.Session()
retry = Retry(connect=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


def timezoneConverter(utc_datetime):
    return utc_datetime.astimezone(timezone('Turkey'))

def get_provinceInfo():
    while True:
        try:
            link = "https://servis.mgm.gov.tr/web/merkezler/iller"
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            response = session.get(link, headers=headers)
            json = response.json()

            provinceInfo = {}
            for index in range(0, len(json)):
                province = json[index]['il']
                provinceInfo.setdefault(province, json[index])
            return provinceInfo
        except:
            logging.warning('İl verisi başarılı bir şekilde alınamadı.')
            continue

def get_districtInfo():
    while True:
        try:
            districtInfo = {}
            link = "https://servis.mgm.gov.tr/web/merkezler/ililcesi?"
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            provinceInfo = get_provinceInfo()
            for province in provinceInfo.keys():
                params = {"il": province}
                response = session.get(link, params=params, headers=headers)
                json = response.json()

                for index in range(0, len(json)):
                    province = json[index]['il']
                    district = json[index]['ilce']
                    districtInfo.setdefault(province, {})
                    districtInfo[province].setdefault(district, json[index])
            return districtInfo
        except:
            logging.warning('İlçe verisi başarılı bir şekilde alınamadı.')
            continue

class instant:
    def __init__(self, il, ilce):
        try: 
            self.province = province
        except NameError: 
            self.province = get_provinceInfo()
        try: 
            self.district = district
        except NameError: 
            self.district = get_districtInfo()
        
        self.il = il
        self.ilce = ilce
        
    def request(self):
        url = "https://servis.mgm.gov.tr/web/sondurumlar?"
        headers = {"Origin": "https://www.mgm.gov.tr/"}
        if self.ilce == None:
            params = {'istno': self.province[self.il]['sondurumIstNo']}
            self.ilce = self.province[self.il]['ilce']
        else:
            params = {'istno': self.district[self.il][self.ilce]['sondurumIstNo']}
        request = session.get(url, params=params, headers=headers)
        json = request.json()
        json = json[0]
        return json

    def check(self):
        self.instantData = self.request()
        #instantData = instantDataRequest(il, ilce)
        #global veriZamani
        self.veriZamani = timezoneConverter(datetime.strptime(self.instantData["veriZamani"], "%Y-%m-%dT%H:%M:%S.%fZ"))
        self.tarih = format(self.veriZamani, "%d/%m/%Y")
        self.saat = format(self.veriZamani, "%H:%M:%S")

        dir = f"work/{self.il}/{self.ilce}/"
        if os.path.exists(dir) == False:
            os.makedirs(dir)
        vt = sqlite3.connect(dir + 'data.db')
        im = vt.cursor()

        command = f"""CREATE TABLE IF NOT EXISTS instantData
        (id INTEGER PRIMARY KEY, İl, İlçe, İstasyonNumarası, Tarih, Saat, Sıcaklık, Hadise, YağışMiktarı, Nem, RüzgarYönü, RüzgarHızı, ABasınç, DİBasınç)"""
        im.execute(command)

        command = f"""SELECT Tarih, Saat FROM instantData
        WHERE Tarih='{self.tarih}' AND Saat='{self.saat}'"""
        self.sonVeri = im.execute(command).fetchall()
        if self.sonVeri != []:
            vt.commit()
            vt.close()
        return self.sonVeri # self.instantData, self.veriZamani, self.tarih, self.saat, 
    
    def sql(self):
        self.check()
            #instantData, veriZamani, tarih, saat, sonVeri = instantDataCheck(il, ilce)
        if self.sonVeri == []:
            dir_list = [
            f"work/{self.il}/{self.ilce}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/{self.veriZamani.month}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/{self.veriZamani.month}/{self.veriZamani.day}/"
        ]
            for dir in dir_list:
                if os.path.exists(dir) == False:
                    os.makedirs(dir)

                vt = sqlite3.connect(dir + 'data.db')
                im = vt.cursor()

                command = f"""CREATE TABLE IF NOT EXISTS instantData
                (id INTEGER PRIMARY KEY, İl, İlçe, İstasyonNumarası, Tarih, Saat, Sıcaklık, Hadise, YağışMiktarı, Nem, RüzgarYönü, RüzgarHızı, ABasınç, DİBasınç)"""
                im.execute(command)

                row = [
                    self.il, self.ilce, self.instantData['istNo'], self.tarih, self.saat, self.instantData['sicaklik'],
                    self.instantData['hadiseKodu'], self.instantData['yagis00Now'],
                    self.instantData['nem'], self.instantData['ruzgarYon'], self.instantData['ruzgarHiz'],
                    self.instantData['aktuelBasinc'], self.instantData['denizeIndirgenmisBasinc']
                ]
                mark = "?" * len(row)
                comma = ","
                mark = comma.join(mark)

                newRow = f"""INSERT INTO instantData 
                (İl, İlçe, İstasyonNumarası, Tarih, Saat, Sıcaklık, Hadise, YağışMiktarı, Nem, RüzgarYönü, RüzgarHızı, ABasınç, DİBasınç) 
                VALUES ({mark})"""

                im.execute(newRow, row)
                vt.commit()
                vt.close()
                self.graph(dir)
    
    def graph(self, dir):
        if os.path.exists(dir) == False:
            os.makedirs(dir)
        vt = sqlite3.connect(dir + 'data.db')
        im = vt.cursor()

        veri = im.execute("""SELECT Tarih, Saat, Sıcaklık, Nem, YağışMiktarı, RüzgarYönü, RüzgarHızı, DİBasınç FROM instantData""").fetchall()
    
        zaman = []
        sicaklik = []
        dewpoint = []
        yagis = [0.0]
        rüzgar_yön = []
        rüzgar_hiz = []
        basinc = []
        nem = []
        yagis_x = []
        for row in veri:
            gün, ay, yıl = row[0].split("/")
            saat, dakika, saniye = row[1].split(":")
    
            zaman.append(datetime(int(yıl), int(ay), int(gün), int(saat), int(dakika),int(saniye)))
            sicaklik.append(float(row[2]))
            yagis.append(float(row[4]))

            N = (m.log(float(row[3])/100)+((17.27*float(row[2]))/(237.3+float(row[2]))))/17.27
            D = (237.3*N)/(1-N)
					
            dewpoint.append(D)
            rüzgar_yön.append(float(row[5]))
            rüzgar_hiz.append(float(row[6]))
            basinc.append(float(row[7]))
            nem.append(float(row[3]))
        
        yagis = list(yagis)
        zaman = list(zaman)
        sicaklik = list(sicaklik)
        dewpoint = list(dewpoint)
        nem = list(nem)
        #y3 = list(y3)
        for index, eleman in enumerate(yagis):
            if eleman<0:
                yagis[index] = 0
        for i in range(1, len(yagis)):
            if yagis[i] < yagis[i-1] :
                yagis_x.append(yagis[i])
            else:
                yagis_x.append(yagis[i]-yagis[i-1])

        f, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(20,20), sharex=True) 
        """
        for ax in [ax1, ax2, ax3, ax4, ax5]:
            for i in range(1, len(zaman)):
                if zaman[i].day != zaman[i-1].day:
                    ax.axvline(zaman[i], color='black', linestyle='-', linewidth=0.3)
        """
        
        
        title = f"""
        METEOGRAM

        - {str(self.il +' '+self.ilce)} -
        ({district[self.il][self.ilce]['sondurumIstNo']})
        """
        plt.suptitle(title, fontsize= 20, fontweight='bold')

        
        left_title = f"""
        {district[self.il][self.ilce]['enlem']}N      {self.district[self.il][self.ilce]['boylam']}E
        Rakım:  {district[self.il][self.ilce]['yukseklik']}m
        """

        ax1.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
        right_title = f"""
        Tarih:  {str(format(zaman[0], "%d/%m/%Y"))}

        """
        
        ax1.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")

        ax1.plot(zaman, sicaklik, "r-", label="Hava Sıcaklığı (°C)")
        ax1.grid(True)
        ax1.set_ylabel("Sıcaklık (°C)")

        ax1.plot(zaman, dewpoint, "g-", label="Çiy Noktası Sıcaklığı (°C)")
        ax1.legend()

        ax2.plot(zaman, nem, label="Bağıl Nem (%)")
        ax2.fill_between(zaman, nem, alpha=0.2)
        ax2.grid(True)
        ax2.set_ylabel("Bağıl Nem (%)")
        ax2.legend()
        
        ax3.bar(zaman, yagis_x, width=.01, label="Yağış Miktarı (mm)")
        ax3.grid(True)
        ax3.set_ylabel("Yağış Miktarı (mm)")
        ax3.legend()

        ax4.plot(zaman, basinc, label="Basınç (mb)")
        ax4.grid(True)
        ax4.set_ylabel("Basınç (mb)")
        ax4.legend()

        ax5.plot(zaman, rüzgar_hiz, label="Rüzgar Hızı (km/h)")
        ax5.grid(True)
        ax5.set_ylabel("Rüzgar Hızı (km/h)")
        ax5.legend()
        
        #plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M') #%d/%m/%Y  
        #plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1)) #
        plt.gca().xaxis.set_minor_locator(mdates.HourLocator(interval=1))
        #plt.gcf().autofmt_xdate()
        locator = mdates.AutoDateLocator()
        formatter = mdates.ConciseDateFormatter(locator)
        plt.gca().xaxis.set_major_locator(locator)
        plt.gca().xaxis.set_major_formatter(formatter)

        #plt.tight_layout(h_pad=0)
        plt.xlabel("Zaman")
        #plt.xticks(rotation=90)
        #f.subplots_adjust(hspace=0)
        #plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        #plt.autoscale()
        #plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(5))
        

        plt.savefig(dir + "meteogram.pdf", dpi=300)
        plt.close()

        vt.commit()
        vt.close()


province = get_provinceInfo()
district = get_districtInfo()

workspace = {
    "Samsun" : None,
    "Amasya" : None,
    "Ordu" : None,
    "Sinop" : None,
    "İstanbul" : "Arnavutköy",
    "Kahramanmaraş" : "Elbistan",
    "Osmaniye" : None,
    "Rize" : None
}

while True:
    keep_alive()
    for il, ilce in workspace.items():
        anlik = instant(il, ilce)
        anlik.sql()