# Gerekli kütüphaneler import edilir.
from requests.adapters import HTTPAdapter
from datetime import datetime, timedelta
from keep_alive import keep_alive
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

# log dosyası oluşturulur.
logging.basicConfig(filename='.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')

logging.debug('Debug mesajı')
logging.info('Info mesajı')
logging.warning('Warning mesajı')
logging.error('Error mesajı')

# Grafik çıktılarının otomatik boyutlandırılması için:
rcParams.update({'figure.autolayout': True})

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
            json = request.json()
            json = json[0]
            return json
        except:
            logging.warning(f"{self.il}/{self.ilce} anlık ölçüm verileri istenirken bir hata meydana geldi.")

    def check(self):
        try:
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
        except:
            logging.warning(f"{self.il}/{self.ilce} anlık ölçüm verileri kontrol edilirken bir hata meydana geldi.")
    
    def sql(self):
        try:
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
            veri = im.execute("""SELECT Tarih, Saat, Sıcaklık, Nem, YağışMiktarı, RüzgarYönü, RüzgarHızı, DİBasınç FROM instantData""").fetchall()
            
            # Veri tabanı dosyası kapatılır.
            vt.close()
            
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
                nem.append(float(row[3]))
                yagis.append(float(row[4]))
                rüzgar_yön.append(float(row[5]))
                rüzgar_hiz.append(float(row[6]))
                basinc.append(float(row[7]))
            
            # Yağış verisindeki hatalar düzeltilir.
            for index, eleman in enumerate(yagis):
                if eleman<0:
                    yagis[index] = yagis[index-1]
            
            # İki ölçüm arasındaki yağış miktarı farkı hesaplanıp liste oluşturulur.
            for i in range(1, len(yagis)):
                if yagis[i] < yagis[i-1] :
                    yagis_x.append(yagis[i])
                else:
                    yagis_x.append(yagis[i]-yagis[i-1])

            # Nem verisindeki hatalar düzeltilir.
            for index, eleman in enumerate(nem):
                if eleman<0:
                    nem[index] = nem[index-1]

            # dewpoint hesaplanır.
            for i in range(0, len(zaman)):
                N = (m.log(nem[i]/100)+((17.27*sicaklik[i])/(237.3+sicaklik[i])))/17.27
                D = (237.3*N)/(1-N)
                dewpoint.append(float(D))

            # Aynı x eksenini kullanan 5 grafik oluşturulur.
            f, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(20,20), sharex=True) 
            """
            for ax in [ax1, ax2, ax3, ax4, ax5]:
                for i in range(1, len(zaman)):
                    if zaman[i].day != zaman[i-1].day:
                        ax.axvline(zaman[i], color='black', linestyle='-', linewidth=0.3)
            """
            
            # Grafik ana başlığı oluşturulur.
            title = f"""
            METEOGRAM

            - {str(self.il +' '+self.ilce)} -
            ({district[self.il][self.ilce]['sondurumIstNo']})
            """
            plt.suptitle(title, fontsize= 20, fontweight='bold')

            # Grafik sol başlığı oluşturulur.
            left_title = f"""
            {district[self.il][self.ilce]['enlem']}N      {self.district[self.il][self.ilce]['boylam']}E
            Rakım:  {district[self.il][self.ilce]['yukseklik']}m
            """
            ax1.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
            
            # Grafik sağ başlığı oluşturulur.
            right_title = f"""
            Tarih:  {str(format(zaman[0], "%d/%m/%Y"))}

            """
            ax1.set_title(right_title, loc='right', fontsize= 18, fontstyle="italic")

            # Sıcaklık grafikleri oluşturulur.
            ax1.plot(zaman, sicaklik, "r-", label="Hava Sıcaklığı (°C)")
            ax1.plot(zaman, dewpoint, "g-", label="Çiy Noktası Sıcaklığı (°C)")
            ax1.set_ylabel("Sıcaklık (°C)")
            ax1.grid(True)
            ax1.legend()

            # Bağıl Nem grafiği oluşturulur.
            ax2.plot(zaman, nem, label="Bağıl Nem (%)")
            ax2.fill_between(zaman, nem, alpha=0.2)
            ax2.set_ylabel("Bağıl Nem (%)")
            ax2.grid(True)
            ax2.legend()
            
            # Yağış miktarı grafiği oluşturulur.
            ax3.bar(zaman, yagis_x, width=.01, label="Yağış Miktarı (mm)")
            ax3.set_ylabel("Yağış Miktarı (mm)")
            ax3.grid(True)
            ax3.legend()

            # Basınç grafiği oluşturulur.
            ax4.plot(zaman, basinc, label="Basınç (mb)")
            ax4.set_ylabel("Basınç (mb)")
            ax4.grid(True)
            ax4.legend()

            # Rüzgar hızı grafiği oluşturulur.
            ax5.plot(zaman, rüzgar_hiz, label="Rüzgar Hızı (km/h)")
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
            plt.gca().xaxis.set_major_locator(locator)
            plt.gca().xaxis.set_major_formatter(formatter)
            plt.gca().xaxis.set_minor_locator(mdates.HourLocator(interval=1))

            #plt.tight_layout(h_pad=0)
            plt.xlabel("Zaman")
            #plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
            #plt.autoscale()
            #plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(5))
            
            # Oluşturulan figür pdf dosyası olarak kaydedilir.
            plt.savefig(dir + "meteogram.pdf", dpi=300)
            plt.close()
        except:
            logging.warning(f"{self.il}/{self.ilce} meteogramı çizilirken bir hata meydana geldi. Dosya konumu: {dir}")

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
                params = {'istno': province[self.il]['gunlukTahminIstNo']}
                self.ilce = self.province[self.il]['ilce']
            else:
                params = {'istno': district[self.il][self.ilce]['gunlukTahminIstNo']}
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            request = session.get(url, params=params, headers=headers)
            json = request.json()
            json = json[0]
            return json
        except:
            logging.warning(f"{self.il}/{self.ilce} günlük tahmin verileri istenirken bir hata meydana geldi.")
    
    def check(self):
        try:
            self.dailyForecastData = self.request()
            self.veriZamani = timezoneConverter(datetime.strptime(self.dailyForecastData["tarihGun1"],"%Y-%m-%dT%H:%M:%S.%fZ")) - timedelta(days=1)
            self.yayinTarih = format(self.veriZamani, "%d/%m/%Y")
            self.yayinSaat = format(self.veriZamani, "%H:%M:%S")

            dir = f"work/{self.il}/{self.ilce}/"
            if os.path.exists(dir) == False:
                    os.makedirs(dir)
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()

            command = f"""CREATE TABLE IF NOT EXISTS dailyForecast
            (İl, İlçe, İstasyonNumarası, YayınTarihi, YayınSaati, Tarih, Saat, Hadise, MinSıcaklık, MaxSıcaklık, MinNem, MaxNem, RüzgarYönü, RüzgarHızı)"""
            im.execute(command)

            command = f"""SELECT YayınTarihi, YayınSaati FROM dailyForecast WHERE YayınTarihi='{self.yayinTarih}' AND YayınSaati='{self.yayinSaat}'"""
            self.sonVeri = im.execute(command).fetchall()
            if self.sonVeri != []:
                vt.commit()
                vt.close()
            return self.sonVeri
        except:
            logging.warning(f"{self.il}{self.ilce} günlük tahmin verileri kontrol edilirken bir hata meydana geldi.")
    
    def sql(self):
        try:
            self.check()
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

                    command = f"""CREATE TABLE IF NOT EXISTS dailyForecast
                    (İl, İlçe, İstasyonNumarası, YayınTarihi, YayınSaati, Tarih, Saat, Hadise, MinSıcaklık, MaxSıcaklık, MinNem, MaxNem, RüzgarYönü, RüzgarHızı)"""
                    im.execute(command)

                    for gun in ["1", "2", "3", "4", "5"]:
                        veriZamani = timezoneConverter(
                            datetime.strptime(self.dailyForecastData["tarihGun" + gun],
                                            "%Y-%m-%dT%H:%M:%S.%fZ"))
                        tarih = format(veriZamani, "%d/%m/%Y")
                        saat = format(veriZamani, "%H:%M:%S")

                        row = [
                            self.il, self.ilce, self.dailyForecastData['istNo'], self.yayinTarih, self.yayinSaat, tarih,
                            saat, self.dailyForecastData['hadiseGun' + gun],
                            self.dailyForecastData['enDusukGun' + gun],
                            self.dailyForecastData['enYuksekGun' + gun],
                            self.dailyForecastData['enDusukNemGun' + gun],
                            self.dailyForecastData['enYuksekNemGun' + gun],
                            self.dailyForecastData['ruzgarYonGun' + gun],
                            self.dailyForecastData['ruzgarHizGun' + gun]
                        ]
                        mark = "?" * len(row)
                        comma = ","
                        mark = comma.join(mark)
                        newRow = f"""INSERT INTO dailyForecast VALUES ({mark})"""
                        im.execute(newRow, row)
                    vt.commit()
                    vt.close()
                    for limit in ["Minimum", "Maksimum"]:
                        self.graph(dir, limit)
        except:
            logging.warning(f"{self.il}/{self.ilce} günlük tahmin verileri veri tabanına yazılırken bir hata meydana geldi.")
    
    def graph(self, dir, limit):
        try:
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()

            command = """SELECT Tarih, MIN(Sıcaklık), MAX(Sıcaklık) FROM instantData GROUP BY Tarih"""
            data = im.execute(command).fetchall()

            x = []
            y = []

            for row in data:
                gün, ay, yıl = row[0].split("/")
                x.append(datetime(int(yıl), int(ay), int(gün)))
                if limit == "Minimum":
                    y.append(row[1])
                elif limit == "Maksimum":
                    y.append(row[2])
            
            f, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(20,20), sharex=True) 
            main_title = f"""
                {self.il} {self.ilce}
                {limit} Sıcaklık
                """
            plt.suptitle(main_title, fontsize= 20, fontweight='bold')

            for i in [1, 2, 3, 4, 5]:
                command = f"""SELECT Tarih, MinSıcaklık, MaxSıcaklık FROM dailyForecast WHERE Tarih - YayınTarihi = {i}"""
                data = im.execute(command).fetchall()

                x2 = []
                y2 = []
                for row in data:
                    x2.append(row[0])
                    if limit == "Minimum":
                        y2.append(row[1])
                    elif limit == "Maksimum":
                        y2.append(row[2])
                
                left_title = f"""
                {i}. Gün {limit} Sıcaklık Tahmini
                """
                if i==1:
                    ax1.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
                    ax1.plot(x, y, "r-", linewidth=2, alpha=0.8, label="Ölçülen Sıcaklık (°C)")
                    ax1.plot(x2, y2, alpha=0.6, label=f"{i}. Gün Tahmini Sıcaklık (°C)")
                    ax1.set_ylabel("Sıcaklık (°C)")
                    ax1.grid(True)
                    ax1.legend()
                elif i==2:
                    ax2.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
                    ax2.plot(x, y, "r-", linewidth=2, alpha=0.8, label="Ölçülen Sıcaklık (°C)")
                    ax2.plot(x2, y2, alpha=0.6, label=f"{i}. Gün Tahmini Sıcaklık (°C)")
                    ax2.set_ylabel("Sıcaklık (°C)")
                    ax2.grid(True)
                    ax2.legend()
                elif i==3:
                    ax3.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
                    ax3.plot(x, y, "r-", linewidth=2, alpha=0.8, label="Ölçülen Sıcaklık (°C)")
                    ax3.plot(x2, y2, alpha=0.6, label=f"{i}. Gün Tahmini Sıcaklık (°C)")
                    ax3.set_ylabel("Sıcaklık (°C)")
                    ax3.grid(True)
                    ax3.legend()
                elif i==4:
                    ax4.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
                    ax4.plot(x, y, "r-", linewidth=2, alpha=0.8, label="Ölçülen Sıcaklık (°C)")
                    ax4.plot(x2, y2, alpha=0.6, label=f"{i}. Gün Tahmini Sıcaklık (°C)")
                    ax4.set_ylabel("Sıcaklık (°C)")
                    ax4.grid(True)
                    ax4.legend()
                elif i==5:
                    ax5.set_title(left_title, loc='left', fontsize= 18, fontstyle="italic")
                    ax5.plot(x, y, "r-", linewidth=2, alpha=0.8, label="Ölçülen Sıcaklık (°C)")
                    ax5.plot(x2, y2, alpha=0.6, label=f"{i}. Gün Tahmini Sıcaklık (°C)")
                    ax5.set_ylabel("Sıcaklık (°C)")
                    ax5.grid(True)
                    ax5.legend()

            plt.xlabel("Zaman")

            locator = mdates.AutoDateLocator()
            formatter = mdates.ConciseDateFormatter(locator)
            plt.gca().xaxis.set_major_locator(locator)
            plt.gca().xaxis.set_major_formatter(formatter)
            #plt.gca().xaxis.set_minor_locator(mdates.HourLocator(interval=1))

            plt.savefig(dir + f"{limit}.pdf", dpi=300)
            plt.close()
            vt.commit()
            vt.close()
        except:
            logging.warning(f"{self.il} {self.ilce} {limit} grafiği çizilemedi. Dosya konumu: {dir}")

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
                params = {'istno': province[self.il]['saatlikTahminIstNo']}
                self.ilce = self.province[self.il]['ilce']
            else:
                params = {'istno': district[self.il][self.ilce]['saatlikTahminIstNo']}
            headers = {"Origin": "https://www.mgm.gov.tr/"}
            request = session.get(url, params=params, headers=headers)
            json = request.json()
            json = json[0]
            return json
        except:
            logging.warning(f"{self.il}/{self.ilce} saatlik tahmin verisi istenirken bir hata meydana geldi.")

    def check(self):
        try:
            self.hourlyForecastData = self.request()
            self.veriZamani = timezoneConverter(datetime.strptime(self.hourlyForecastData['baslangicZamani'],"%Y-%m-%dT%H:%M:%S.%fZ"))
            self.yayinTarih = format(self.veriZamani, "%d/%m/%Y")
            self.yayinSaat = format(self.veriZamani, "%H:%M:%S")

            dir = f"work/{self.il}/{self.ilce}/"
            if os.path.exists(dir) == False:
                os.makedirs(dir)
            vt = sqlite3.connect(dir + 'data.db')
            im = vt.cursor()

            command = f"""CREATE TABLE IF NOT EXISTS hourlyForecast
            (İl, İlçe, İstasyonNumarası, YayınTarihi, YayınSaati, Tarih, BaşlangıçSaati, BitişSaati, BeklenenHadise, Sıcaklık, HissedilenSıcaklık, Nem, RüzgarYönü, OrtRüzgarHızı, MaksRüzgarHızı)"""
            im.execute(command)

            command = f"""SELECT YayınTarihi, YayınSaati FROM hourlyForecast 
            WHERE YayınTarihi='{self.yayinTarih}' AND YayınSaati='{self.yayinSaat}'"""
            self.sonVeri = im.execute(command).fetchall()
            if self.sonVeri != []:
                vt.commit()
                vt.close()

            return self.sonVeri
        except:
            logging.warning(f"{self.il}/{self.ilce} saatlik tahmin verisi kontrol edilirken bir hata meydana geldi.")

    def sql(self):
        try:
            self.check()
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

                    command = f"""CREATE TABLE IF NOT EXISTS hourlyForecast
                    (İl, İlçe, İstasyonNumarası, YayınTarihi, YayınSaati, Tarih, BaşlangıçSaati, BitişSaati, BeklenenHadise, Sıcaklık, HissedilenSıcaklık, Nem, RüzgarYönü, OrtRüzgarHızı, MaksRüzgarHızı)"""

                    im.execute(command)

                    for hourlyForecast in self.hourlyForecastData["tahmin"]:
                        self.veriZamani = timezoneConverter(datetime.strptime(hourlyForecast['tarih'],"%Y-%m-%dT%H:%M:%S.%fZ"))
                        self.tarih = format(self.veriZamani, "%d/%m/%Y")
                        self.baslangicSaat = format(self.veriZamani - timedelta(hours=3), "%H:%M:%S")
                        self.bitisSaat = format(self.veriZamani, "%H:%M:%S")
                        row = [
                            self.il, self.ilce, self.hourlyForecastData['istNo'], self.yayinTarih, self.yayinSaat,
                            self.tarih, self.baslangicSaat, self.bitisSaat, hourlyForecast['hadise'],
                            hourlyForecast['sicaklik'], hourlyForecast['hissedilenSicaklik'],
                            hourlyForecast['nem'], hourlyForecast['ruzgarYonu'],
                            hourlyForecast['ruzgarHizi'], hourlyForecast['maksimumRuzgarHizi']
                        ]
                        mark = "?" * len(row)
                        comma = ","
                        mark = comma.join(mark)
                        newRow = f"""INSERT INTO hourlyForecast VALUES ({mark})"""

                        im.execute(newRow, row)

                    vt.commit()
                    vt.close()
                    self.graph()
        except:
            logging.warning(f"{self.il}/{self.ilce} saatlik tahmin verileri veri tabanına eklenirken bir hata meydana geldi.")

    def graph(self):
        pass


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

keep_alive()
while True:
    for il, ilce in workspace.items():
        anlik = instant(il, ilce)
        anlik.sql()

        saatlik = hourlyForecast(il, ilce)
        saatlik.sql()

        günlük = dailyForecast(il, ilce)
        günlük.sql()