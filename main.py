# Gerekli kütüphaneler import edilir.
from requests.adapters import HTTPAdapter
from datetime import datetime, timedelta
from keep_alive import keep_alive
from windrose import WindroseAxes
import matplotlib
matplotlib.use('agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import rcParams
from urllib3.util import Retry
from pytz import timezone
import math as m
import requests
import logging
import sqlite3
import os
import locale

#plt.style.use('ggplot')
#plt.rcParams['axes.prop_cycle'] = plt.cycler(color=plt.cm.Dark2.colors)

locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
# log dosyası oluşturulur.
logging.basicConfig(filename='.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

logging.debug('Debug mesajı')
logging.info('Info mesajı')
logging.warning('Warning mesajı')
logging.error('Error mesajı')

# Grafik çıktılarının otomatik boyutlandırılması için:
#rcParams.update({'figure.autolayout': True})

# API isteğinde çok fazla deneme hatası almamak için:
session = requests.Session()
retry = Retry(connect=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Global saatin yerel saate dönüştürülmesi için gerekli fonksiyon
def timezoneConverter(utc_datetime):
    return utc_datetime.astimezone(timezone('Turkey'))

# Her ilin merkez ilçesinde bulunan istasyonların bilgileri
def get_provinceInfo():
    while True:
        try:
            link = "https://servis.mgm.gov.tr/web/merkezler/iller"
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            request = session.get(link, headers=headers)
            response = request.json()
            provinceInfo = {}
            for index in range(len(response)):
                province = response[index]['il']
                provinceInfo.setdefault(province, response[index])
            return provinceInfo
        except:
            logging.error('İllerin merkez ilçelerine ait bilgiler başarılı bir şekilde alınamadı.')

# Her ilin her ilçesinde bulunan istasyonların bilgileri
def get_districtInfo():
    while True:
        try:
            districtInfo = {}
            link = "https://servis.mgm.gov.tr/web/merkezler/ililcesi?"
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            provinceInfo = get_provinceInfo()
            for province in provinceInfo.keys():
                params = {"il": province}
                request = session.get(link, params=params, headers=headers)
                response = request.json()
                for index in range(0, len(response)):
                    province = response[index]['il']
                    district = response[index]['ilce']
                    districtInfo.setdefault(province, {})
                    districtInfo[province].setdefault(district, response[index])
            return districtInfo
        except:
            logging.error('İllerin ilçelerine ait bilgiler başarılı bir şekilde alınamadı.')
    
# Anlık ölçüm verileri için:
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
        try:
            url = "https://servis.mgm.gov.tr/web/sondurumlar?"
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            if self.ilce == None:
                params = {'istno': self.province[self.il]['sondurumIstNo']}
                self.ilce = self.province[self.il]['ilce']
            else:
                params = {'istno': self.district[self.il][self.ilce]['sondurumIstNo']}
            request = session.get(url, params=params, headers=headers)
            response = request.json()
            response = response[0]
            return response
        except:
            logging.error(f"{self.il}/{self.ilce} anlık ölçüm verileri istenirken bir hata meydana geldi.")

    def check(self):
        try:
            self.instantData = self.request()
            self.veriZamani = datetime.strptime(self.instantData["veriZamani"], "%Y-%m-%dT%H:%M:%S.%fZ")
            dir = f"work/{self.il}/{self.ilce}/"
            if os.path.exists(dir) == False:
                os.makedirs(dir)     
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()
            im.execute("CREATE TABLE IF NOT EXISTS instantData ({})".format(", ".join([f"{key}" for key in self.instantData.keys()])))
            sonVeri = im.execute("SELECT veriZamani FROM instantData WHERE veriZamani='{}'".format(self.instantData["veriZamani"])).fetchall()
            vt.commit()
            vt.close()
            return sonVeri 
        except:
            logging.error(f"{self.il}/{self.ilce} anlık ölçüm verileri kontrol edilirken bir hata meydana geldi.")
    
    def sql(self):
        sonVeri = self.check()
        dir_list = [
            f"work/{self.il}/{self.ilce}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/{self.veriZamani.month}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/{self.veriZamani.month}/{self.veriZamani.day}/"
        ]
        try:
            if sonVeri == []:
                for dir in dir_list:
                    if os.path.exists(dir) == False:
                        os.makedirs(dir)
                    vt = sqlite3.connect(dir + 'data.db')
                    im = vt.cursor()
                    im.execute("CREATE TABLE IF NOT EXISTS instantData ({})".format(", ".join([f"{key}" for key in self.instantData.keys()])))
                    im.execute("INSERT INTO instantData ({}) VALUES ({})".format(", ".join(self.instantData.keys()), ", ".join(["?" for _ in range(len(self.instantData))])), [values for values in self.instantData.values()])
                    vt.commit()
                    vt.close()
                    self.graph(dir)
        except:
            logging.warning(f"{self.il}/{self.ilce} anlık ölçüm verileri veri tabanına yazılırken bir hata meydana geldi.")
                      
    def graph(self, dir):
        try:
            # dir yolu mevcut değilse oluşturulur.
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            # Veri tabanı dosyasına bağlanılır.
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()
            # Veriler bir değişkene atanır.
            veri = im.execute("""SELECT veriZamani, sicaklik, nem, yagis00Now, ruzgarYon, ruzgarHiz, denizeIndirgenmisBasinc FROM instantData""").fetchall()
            # Veri tabanı dosyası kapatılır.
            vt.close()
            
            veriZamani = []
            sicaklik = []
            nem = []
            dewpoint = []
            yagis = [0.0]
            yagisFark = []
            toplamYagis = {}
            ruzgarYon = []
            ruzgarHiz = []
            denizeIndirgenmisBasinc = []

            for row in veri:
                veriZamani.append(timezoneConverter(datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S.%fZ")))
                sicaklik.append(float(row[1]))
                nem.append(float(row[2]))
                yagis.append(float(row[3]))
                ruzgarYon.append(float(row[4]))
                ruzgarHiz.append(float(row[5]))
                denizeIndirgenmisBasinc.append(float(row[6]))
            
            # Verilerdeki hatalar düzeltilir.
            for degisken in [nem, yagis, ruzgarHiz, denizeIndirgenmisBasinc]:
                for index, eleman in enumerate(degisken):
                    if eleman<0:
                        degisken[index] = degisken[index-1]
            # İki ölçüm arasındaki yağış miktarı farkı hesaplanıp liste oluşturulur.
            for i in range(1, len(yagis)):
                toplamYagis[veriZamani[i-1].date()] = yagis[i]
                if yagis[i] < yagis[i-1] :
                    yagisFark.append(yagis[i])
                else:
                    yagisFark.append(yagis[i]-yagis[i-1])      
            # dewpoint hesaplanır.
            for i in range(len(veriZamani)):
                N = (m.log(nem[i]/100)+((17.27*sicaklik[i])/(237.3+sicaklik[i])))/17.27
                D = (237.3*N)/(1-N)
                dewpoint.append(float(D))
            # Aynı x eksenini kullanan 5 grafik oluşturulur.
            f, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(20,20), sharex=True) 
            # Grafik ana başlığı oluşturulur.
            title = f"METEOGRAM\n- {str(self.il +' '+self.ilce)} -\n({self.district[self.il][self.ilce]['sondurumIstNo']})"
            plt.suptitle(title, fontsize= 20, fontweight='bold')
            # Grafik sol başlığı oluşturulur.
            left_title = f"{self.district[self.il][self.ilce]['enlem']}N      {self.district[self.il][self.ilce]['boylam']}E\nRakım:  {self.district[self.il][self.ilce]['yukseklik']}m"
            ax1.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
            # Grafik sağ başlığı oluşturulur.
            right_title = f"Başlangıç Tarihi:  {str(format(veriZamani[0], '%d %B %Y %A'))}\nBitiş Tarihi:  {str(format(veriZamani[-1], '%d %B %Y %A'))}"
            ax1.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")
            # Sıcaklık grafikleri oluşturulur.
            ax1.plot(veriZamani, sicaklik, "r-", label="Hava Sıcaklığı (°C)")
            ax1.plot(veriZamani, dewpoint, "g-", label="Çiy Noktası Sıcaklığı (°C)")
            ax1.set_ylabel("Sıcaklık (°C)")
            ax1.grid(True)
            ax1.legend()
            # Bağıl Nem grafiği oluşturulur.
            ax2.plot(veriZamani, nem, label="Bağıl Nem (%)")
            ax2.fill_between(veriZamani, nem, alpha=0.2)
            ax2.set_ylabel("Bağıl Nem (%)")
            ax2.grid(True)
            ax2.legend()
            # Yağış miktarı grafiği oluşturulur.
            ax3.bar(toplamYagis.keys(), toplamYagis.values(), label="Toplam Yağış Miktarı (mm)", alpha=0.4, width=1, align="edge")
            ax3.set_ylabel("Yağış Miktarı (mm)")
            ax3.grid(True)
            ax3.legend()
            ax3 = ax3.twinx()
            ax3.bar(veriZamani, yagisFark, label="Yağış Miktarı (mm)", width=.01, align="edge")
            # Basınç grafiği oluşturulur.
            ax4.plot(veriZamani, denizeIndirgenmisBasinc, label="Basınç (mb)")
            ax4.set_ylabel("Basınç (mb)")
            ax4.grid(True)
            ax4.legend()
            # Rüzgar hızı grafiği oluşturulur.
            ax5.plot(veriZamani, ruzgarHiz, label="Rüzgar Hızı (km/h)")
            ax5.set_ylabel("Rüzgar Hızı (km/h)")
            ax5.grid(True)
            ax5.legend()     
            # Grafik ekseni ile ilgili kullanılabilecek kodlar:
            """
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M') #%d/%m/%Y  
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1)) #
            plt.gcf().autofmt_xdate()
            """
            # x ekseni belirteçleri için gerekli ayarlar yapılır.
            locator = mdates.AutoDateLocator()
            formatter = mdates.ConciseDateFormatter(locator)
            f.gca().xaxis.set_major_locator(locator)
            f.gca().xaxis.set_major_formatter(formatter)
            f.gca().xaxis.set_minor_locator(mdates.HourLocator(interval=1))
            f.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.xlabel("Zaman")
            #ax = f.add_subplot(1, 1, 1, projection="windrose") 
            # Oluşturulan figür pdf dosyası olarak kaydedilir.
            f.tight_layout()
            f.savefig(dir + "meteogram.pdf", format='pdf', dpi=300)
            plt.close(f)
        except:
            logging.error(f"{self.il}/{self.ilce} meteogramı çizilirken bir hata meydana geldi. Dosya konumu: {dir}")
        try:
            # Windrose grafiği çizilir.
            fig = plt.figure(figsize=(8,8))
            rect = [0.1, 0.1, 0.8, 0.8]
            ax = WindroseAxes(fig, rect)
            fig.add_axes(ax)
            ax.bar(ruzgarYon, ruzgarHiz)
            ax.set_legend()
            fig.set_in_layout(False)
            fig.savefig(dir + "windrose.pdf", format="pdf", dpi=300)
            plt.close(fig)
        except:
            logging.error(f"{self.il}/{self.ilce} windrose grafiği çizilirken bir hata meydana geldi. Dosya konumu: {dir}")

# Günlük tahmin verileri için:
class dailyForecast:
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
        try:
            url = "https://servis.mgm.gov.tr/web/tahminler/gunluk?"
            if self.ilce == None:
                params = {'istno': self.province[self.il]['gunlukTahminIstNo']}
                self.ilce = self.province[self.il]['ilce']
            else:
                params = {'istno': self.district[self.il][self.ilce]['gunlukTahminIstNo']}
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            request = session.get(url, params=params, headers=headers)
            response = request.json()
            response = response[0]
            return response
        except:
            logging.error(f"{self.il}/{self.ilce} günlük tahmin verileri istenirken bir hata meydana geldi.")
    
    def check(self):
        try:
            self.dailyForecastData = self.request()
            self.veriZamani = datetime.strptime(self.dailyForecastData["tarihGun1"],"%Y-%m-%dT%H:%M:%S.%fZ") 
            self.zamanKontrol = format(datetime.now(), "%Y-%m-%dT%H:%M:%S.%fZ")

            dir = f"work/{self.il}/{self.ilce}/"
            if os.path.exists(dir) == False:
                    os.makedirs(dir)
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()
            im.execute("CREATE TABLE IF NOT EXISTS dailyForecast (baslangicZamani, {})".format(", ".join([f"{key}" for key in self.dailyForecastData.keys()])))
            sonVeri = im.execute("SELECT tarihGun1 FROM dailyForecast WHERE tarihGun1='{}'".format(self.dailyForecastData["tarihGun1"])).fetchall()
            vt.commit()
            vt.close()
            return sonVeri
        except:
            logging.error(f"{self.il}{self.ilce} günlük tahmin verileri kontrol edilirken bir hata meydana geldi.")
    
    def sql(self):
        try:
            sonVeri = self.check()
            dir_list = [
            f"work/{self.il}/{self.ilce}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/{self.veriZamani.month}/",
            f"work/{self.il}/{self.ilce}/{self.veriZamani.year}/{self.veriZamani.month}/{self.veriZamani.day}/"
        ]
            if sonVeri == []:
                for dir in dir_list:
                    if os.path.exists(dir) == False:
                        os.makedirs(dir)
                    vt = sqlite3.connect(dir + 'data.db')
                    im = vt.cursor()
                    im.execute("CREATE TABLE IF NOT EXISTS dailyForecast (baslangicZamani, {})".format(", ".join([f"{key}" for key in self.dailyForecastData.keys()])))
                    a = [self.zamanKontrol]
                    [a.append(values) for values in self.dailyForecastData.values()]
                    im.execute("INSERT INTO dailyForecast (baslangicZamani, {}) VALUES ({})".format(", ".join(self.dailyForecastData.keys()), ", ".join(["?" for _ in range(len(self.dailyForecastData)+1)])), a)
                    vt.commit()
                    vt.close()
                    for limit in ["Minimum", "Maksimum"]:
                        self.graph(dir, limit)
        except:
            logging.error(f"{self.il}/{self.ilce} günlük tahmin verileri veri tabanına yazılırken bir hata meydana geldi.")
                
    def graph(self, dir, limit):
        try:
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()
            def cizgi(maxi, mini):
                # Ölçüm verilerinin tanımlanması
                if limit=="Maksimum":
                    for row in maxi: 
                        xymax.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[1])
                        maxSaat.append(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")))
                if limit=="Minimum":
                    for row in mini: 
                        xymin.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[1])
                        minSaat.append(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")))
                if limit=="Minimum ve Maksimum":
                    for row in maxi: 
                        xymax.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[1])
                        maxSaat.append(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")))
                    for row in mini:
                        xymin.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[1])
                        minSaat.append(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")))

                for number in [1,5]:
                    f, axs = plt.subplots(number, 1, figsize=(20,20), sharex=True, sharey=True)
                    main_title = f"{self.il} {self.ilce}\n({self.district[self.il][self.ilce]['sondurumIstNo']})\n{limit} Sıcaklık"
                    f.suptitle(main_title, fontsize= 20, fontweight='bold')
                    if number==1:
                        sozluk = {1 : axs, 2 : axs, 3 : axs, 4 : axs, 5 : axs}
                        if limit=="Maksimum":
                            axs.plot(xymax.keys(), xymax.values(), "r-", linewidth=2, alpha=0.8, label="Ölçülen Sıcaklık (°C)")
                        if limit=="Minimum":
                            axs.plot(xymin.keys(), xymin.values(), "r-", linewidth=2, alpha=0.8, label="Ölçülen Sıcaklık (°C)")
                        if limit == "Minimum ve Maksimum":
                                axs.bar(xymax.keys(), xymax.values(), label="Ölçülen Maksimum Sıcaklık (°C)")    
                                axs.bar(xymin.keys(), xymin.values(), label="Ölçülen Minimum Sıcaklık (°C)")
                    else:
                        sozluk = {}
                        for gun, ax in enumerate(axs):
                            if limit == "Maksimum":
                                ax.plot(xymax.keys(), xymax.values(), "r-", linewidth=2, alpha=0.8, label="Ölçülen Maksimum Sıcaklık (°C)")
                            if limit == "Minimum":
                                ax.plot(xymin.keys(), xymin.values(), "r-", linewidth=2, alpha=0.8, label="Ölçülen Minimum Sıcaklık (°C)")
                            if limit == "Minimum ve Maksimum":
                                ax.bar(xymax.keys(), xymax.values(), label="Ölçülen Maksimum Sıcaklık (°C)")
                                ax.bar(xymin.keys(), xymin.values(), label="Ölçülen Minimum Sıcaklık (°C)")
                            sozluk.setdefault(gun+1, ax)
    
                    for gun, ax in sozluk.items():
                        liste = [f"tarihGun{gun}", f"enDusukGun{gun}", f"enYuksekGun{gun}"]
                        data = im.execute("SELECT {},{},{} FROM dailyForecast".format(liste[0], liste[1], liste[2])).fetchall()
                        xy2max = {}
                        xy2min = {}
                        # Tahmin verilerinin tanımlanması
                        for row in data:
                            if limit == "Minimum":
                                xy2min.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[1])
                            if limit == "Maksimum":
                                xy2max.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[2])
                            if limit == "Minimum ve Maksimum":
                                xy2max.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[2])
                                xy2min.setdefault(timezoneConverter(datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S.%fZ")).date(), row[1])
                        if number == 1:
                            if limit == "Maksimum":
                                right_title = f"Başlangıç Tarihi:  {str(format(xymax.keys()[0], '%d %B %Y %A'))}\nBitiş Tarihi:  {str(format(xymax.keys()[-1], '%d %B %Y %A'))}"                
                                ax.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")
                            if limit == "Minimum":
                                right_title = f"Başlangıç Tarihi:  {str(format(xymin.keys()[0], '%d %B %Y %A'))}\nBitiş Tarihi:  {str(format(xymin.keys()[-1], '%d %B %Y %A'))}"                
                                ax.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")
                        if number != 1:              
                            left_title = f"{gun}. Gün {limit} Sıcaklık Tahmini"                
                            ax.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
                  
                            if  limit == "Maksimum":
                                HKT = 0
                                n = 0
                                for k in xymax.keys():
                                    if (k in xymax.keys()) and (k in xy2max.keys()):
                                        HKT += (xymax[k]-xy2max[k])**2
                                        n += 1  
                                HKOK = m.sqrt(HKT/n)
                                right_title = f"HKOK: {HKOK}"                
                                ax.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")
                            if limit == "Minimum":
                                HKT = 0
                                n = 0
                                for i,j in zip(xymin.values(), xy2min.values()):
                                    HKT += (i-j)**2
                                    n += 1
                                HKOK = m.sqrt(HKT/n)
                                right_title = f"HKOK: {HKOK}"                
                                ax.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")

                        # Tahmin değerlerinin çizimi
                        if  limit == "Maksimum":
                            ax.plot(xy2max.keys(), xy2max.values(), alpha=0.6, label=f"{gun}. Gün Tahmini Sıcaklık (°C)")
                            ax.set_ylabel("Sıcaklık (°C)")
                            ax.grid(True)
                            ax.legend()
                        if limit == "Minimum":
                            ax.plot(xy2min.keys(), xy2min.values(), alpha=0.6, label=f"{gun}. Gün Tahmini Sıcaklık (°C)")
                            ax.set_ylabel("Sıcaklık (°C)")
                            ax.grid(True)
                            ax.legend()
                        if limit == "Minimum ve Maksimum":
                            #ax.scatter(xy2max.keys(), xy2max.values(), label=f"{gun}. Gün Tahmini Maksimum Sıcaklık (°C)") 
                            #ax.scatter(xy2min.keys(), xy2min.values(), label=f"{gun}. Gün Tahmini Minimum Sıcaklık (°C)") 
                            #for i,j in xymax.items():
                                #ax.annotate(f"{j}", xy=(i,j//2), xycoords='data')
                            #for i,j in xymin.items():
                                #ax.annotate(f"{j}", xy=(i,j//2), xycoords='data')
  
                            left_title = f"Maksimum: {max(xymax.values())}\nMinimum: {min(xymin.values())}"
                            ax.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
                            right_title = f"Başlangıç Tarihi:   {str(format(min(xymin.keys()), '%d %B %Y %A'))}\nBitiş Tarihi:    {str(format(max(xymax.keys()), '%d %B %Y %A'))}"
                            ax.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")
                            ax.set_ylabel("Sıcaklık (°C)")
                            ax.grid(True)
                            ax.legend()
                        
                        # Zaman etiketleri
                        #if limit=="Maksimum":
                            #for i, j, k in zip(xymax.keys(), xymax.values(), maxSaat):
                                #ax.annotate(format(k, "%H:%M"), xy=(i,j), xycoords='data', xytext=(-30,-30), textcoords='offset points',  bbox=dict(boxstyle="round4", fc="w"), arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-0.2", fc="w"))
                        #if limit=="Minimum":
                            #for i, j, k in zip(xymin.keys(), xymin.values(), minSaat):
                                #ax.annotate(format(k, "%H:%M"), xy=(i,j), xycoords='data', xytext=(-30,30), textcoords='offset points',  bbox=dict(boxstyle="round4", fc="w"), arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-0.2", fc="w"))
                        #if limit=="Minimum ve Maksimum":
                            #for i, j, k in zip(xymax.keys(), xymax.values(), maxSaat):
                                #ax.annotate(format(k, "%H:%M"), xy=(i,j), xycoords='data', xytext=(-30,30), textcoords='offset points',  bbox=dict(boxstyle="round4", fc="w"), arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-0.2", fc="w"))
                            #for i, j, k in zip(xymin.keys(), xymin.values(), minSaat):
                                #ax.annotate(format(k, "%H:%M"), xy=(i,j), xycoords='data', xytext=(-30,-30), textcoords='offset points',  bbox=dict(boxstyle="round4", fc="w"), arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-0.2", fc="w"))

                    locator = mdates.AutoDateLocator()
                    formatter = mdates.ConciseDateFormatter(locator)
                    plt.gca().xaxis.set_major_locator(locator)
                    plt.gca().xaxis.set_major_formatter(formatter)
                    plt.gca().xaxis.set_minor_locator(mdates.HourLocator(interval=1))
                    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    plt.xlabel("Zaman")
                    f.tight_layout()
                    plt.savefig(dir + f"{limit}_{number}.pdf", dpi=300)
                    plt.close(f) 
                      
            xymax = {}
            xymin = {}
            maxSaat = []
            minSaat = []

            if limit == "Maksimum":
                data = im.execute("SELECT veriZamani, max(sicaklik) FROM instantData WHERE time(veriZamani) BETWEEN '06:00:00' AND '18:00:00' GROUP BY date(veriZamani)").fetchall()
                cizgi(data, "Maksimum")
            if limit == "Minimum":
                data = im.execute("SELECT veriZamani, min(sicaklik) FROM instantData WHERE veriZamani BETWEEN strftime('%Y-%m-%dT18:00:00', veriZamani, '-1 day') AND strftime('%Y-%m-%dT06:00:00', veriZamani) GROUP BY strftime('%Y-%m-%d', veriZamani)").fetchall()
                cizgi("Minimum", data)
            if limit == "Minimum ve Maksimum":
                maxi = im.execute("SELECT veriZamani, max(sicaklik) FROM instantData WHERE time(veriZamani) BETWEEN '06:00:00' AND '18:00:00' GROUP BY date(veriZamani)").fetchall()
                mini = im.execute("SELECT veriZamani, min(sicaklik) FROM instantData WHERE veriZamani BETWEEN strftime('%Y-%m-%dT18:00:00', veriZamani, '-1 day') AND strftime('%Y-%m-%dT06:00:00', veriZamani) GROUP BY strftime('%Y-%m-%d', veriZamani)").fetchall()
                cizgi(maxi, mini)
              
            vt.commit()
            vt.close()
        except:
            logging.error(f"{self.il} {self.ilce} {limit} grafiği çizilemedi. Dosya konumu: {dir}")

# Saatlik tahmin verileri için:
class hourlyForecast:
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
        try:
            url = "https://servis.mgm.gov.tr/web/tahminler/saatlik?"
            if self.ilce == None:
                params = {'istno': self.province[self.il]['saatlikTahminIstNo']}
                self.ilce = self.province[self.il]['ilce']
            else:
                params = {'istno': self.district[self.il][self.ilce]['saatlikTahminIstNo']}
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            request = session.get(url, params=params, headers=headers)
            response = request.json()
            response = response[0]
            return response
        except:
            logging.error(f"{self.il}/{self.ilce} saatlik tahmin verisi istenirken bir hata meydana geldi.")

    def check(self):
        try:
            self.hourlyForecastData = self.request()
            self.veriZamani = datetime.strptime(self.hourlyForecastData['baslangicZamani'],"%Y-%m-%dT%H:%M:%S.%fZ")
            #self.zamanKontrol = format(self.veriZamani, "%Y-%m-%dT%H:%M:%S.%fZ")
            dir = f"work/{self.il}/{self.ilce}/"
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()
            im.execute("CREATE TABLE IF NOT EXISTS hourlyForecast (baslangicZamani, istNo, merkez, {})".format(", ".join([f"{key}" for key in self.hourlyForecastData["tahmin"][0].keys()])))
            sonVeri = im.execute("SELECT baslangicZamani FROM hourlyForecast WHERE baslangicZamani='{}'".format(self.hourlyForecastData["baslangicZamani"])).fetchall()
            vt.commit()
            vt.close()
            return sonVeri
        except:
            logging.error(f"{self.il}/{self.ilce} saatlik tahmin verisi kontrol edilirken bir hata meydana geldi.")

    def sql(self):
        try:
            sonVeri = self.check()
            if sonVeri == []:
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
                    im.execute("CREATE TABLE IF NOT EXISTS hourlyForecast (baslangicZamani, istNo, merkez, {})".format(", ".join([f"{key}" for key in self.hourlyForecastData["tahmin"][0].keys()])))
                    for index in range(len(self.hourlyForecastData["tahmin"])):
                        a = [self.hourlyForecastData["baslangicZamani"], self.hourlyForecastData["istNo"], self.hourlyForecastData["merkez"]]
                        [a.append(values) for values in self.hourlyForecastData["tahmin"][index].values()]
                        im.execute("INSERT INTO hourlyForecast (baslangicZamani, istNo, merkez, {}) VALUES ({})".format(", ".join(self.hourlyForecastData["tahmin"][index].keys()), ", ".join(["?" for _ in range(len(self.hourlyForecastData["tahmin"][index])+3)])), a)
                    vt.commit()
                    vt.close()
                    #self.graph()
        except:
            logging.error(f"{self.il}/{self.ilce} saatlik tahmin verileri veri tabanına eklenirken bir hata meydana geldi.")

    def graph(self, dir):
         # dir yolu mevcut değilse oluşturulur.
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            # Veri tabanı dosyasına bağlanılır.
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()
            # Veriler bir değişkene atanır.
            datas = im.execute("""SELECT baslangicZamani FROM hourlyForecast GROUP BY strftime('%Y-%m-%d', baslangicZamani)""").fetchall()
            # Veri tabanı dosyası kapatılır.
            f, axs = plt.subplots(3, 1, figsize=(20,20), sharex=True)
            title = f"""
            METEOGRAM

            - {str(self.il +' '+self.ilce)} -
            ({self.district[self.il][self.ilce]['sondurumIstNo']})
            """
            plt.suptitle(title, fontsize= 20, fontweight='bold')
            # Grafik sol başlığı oluşturulur.
            left_title = f"""
            {self.district[self.il][self.ilce]['enlem']}N      {self.district[self.il][self.ilce]['boylam']}E
            Rakım:  {self.district[self.il][self.ilce]['yukseklik']}m
            """
            axs[0].set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
            # Grafik sağ başlığı oluşturulur.
            # ---
            for data in datas:
                for number, tahmin in enumerate(data):
                    print(tahmin)
                    veriler = im.execute("SELECT baslangicZamani, tarih, sicaklik, nem, ruzgarYonu, ruzgarHizi FROM hourlyForecast WHERE baslangicZamani = '{}'".format(tahmin)).fetchall()
                
                    baslangicZamani = []
                    tarih = []
                    sicaklik = []
                    nem = []
                    ruzgarYon = []
                    ruzgarHiz = []
                    print(veriler[0])
                    for row in veriler:
                        baslangicZamani.append(datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S.%fZ"))

                        #tarih.append(datetime.strptime(row[1], "%Y-%m-%dT%H:%M:%S.%fZ") - timedelta(hours=-3))
                        tarih.append(datetime.strptime(row[1], "%Y-%m-%dT%H:%M:%S.%fZ"))

                        #sicaklik.append(float(row[2]))
                        sicaklik.append(float(row[2]))

                        #nem.append(float(row[3]))
                        nem.append(float(row[3]))

                        #ruzgarYon.append(float(row[4]))
                        ruzgarYon.append(float(row[4]))

                        #ruzgarHiz.append(float(row[5]))
                        ruzgarHiz.append(float(row[5]))

                    axs[0].plot(tarih, sicaklik, label="Tahmini Sıcaklık (°C)")
                    axs[0].legend()
                    axs[1].plot(tarih, nem, label="Tahmini Bağıl Nem (%)")
                    axs[1].legend()
                    #axs[1].fill_between(tarih, nem, alpha=0.2)
                    axs[2].plot(tarih, ruzgarHiz, label="Tahmini Rüzgar Hızı (km/h)")
                    axs[2].legend()
                
                    plt.savefig(dir + f"{number}.pdf", dpi=300)

province = get_provinceInfo()
district = get_districtInfo()

# Çalışma alanı belirlenir. 
# İlçe girilmeyecek veya ilin merkez ilçesinden veri alınacaksa None değeri verilir.
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

## TEST KODU
#anlik = instant("Samsun", "Atakum")
#anlik.graph("work/Samsun/Atakum/")
#saatlik = hourlyForecast("Samsun", "Atakum")
#saatlik.sql()
#günlük = dailyForecast("Samsun", "Atakum")
#günlük.graph("work/Samsun/Atakum/", "Minimum")
#günlük.graph("work/Samsun/Atakum/", "Maksimum ve Minimum")

while 1:
    keep_alive()
    while 1:
        for il, ilce in workspace.items():
            anlik = instant(il, ilce)
            anlik.sql()

            saatlik = hourlyForecast(il, ilce)
            saatlik.sql()

            günlük = dailyForecast(il, ilce)
            günlük.sql()