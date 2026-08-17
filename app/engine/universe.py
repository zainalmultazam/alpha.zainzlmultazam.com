# Daftar Saham Likuid IDX (Kompas100 / High Liquidity Universe)
# Menghindari saham gorengan illiquid yang berisiko manipulasi

IDX_STOCKS = [
    # Perbankan & Finansial
    {"ticker": "BBCA.JK", "name": "Bank Central Asia", "sector": "Finance"},
    {"ticker": "BBRI.JK", "name": "Bank Rakyat Indonesia", "sector": "Finance"},
    {"ticker": "BMRI.JK", "name": "Bank Mandiri", "sector": "Finance"},
    {"ticker": "BBNI.JK", "name": "Bank Negara Indonesia", "sector": "Finance"},
    {"ticker": "BRIS.JK", "name": "Bank Syariah Indonesia", "sector": "Finance"},
    {"ticker": "BBTN.JK", "name": "Bank Tabungan Negara", "sector": "Finance"},
    {"ticker": "ARTO.JK", "name": "Bank Jago", "sector": "Finance"},
    {"ticker": "BDMN.JK", "name": "Bank Danamon Indonesia", "sector": "Finance"},
    {"ticker": "BNGA.JK", "name": "Bank CIMB Niaga", "sector": "Finance"},
    
    # Otomotif & Konglomerasi
    {"ticker": "ASII.JK", "name": "Astra International", "sector": "Industrial"},
    {"ticker": "AUTO.JK", "name": "Astra Otoparts", "sector": "Industrial"},
    {"ticker": "GJTL.JK", "name": "Gajah Tunggal", "sector": "Industrial"},
    
    # Energi, Batu Bara & Migas
    {"ticker": "ADRO.JK", "name": "Adaro Energy Indonesia", "sector": "Energy"},
    {"ticker": "PTBA.JK", "name": "Bukit Asam", "sector": "Energy"},
    {"ticker": "MEDC.JK", "name": "Medco Energi Internasional", "sector": "Energy"},
    {"ticker": "PGAS.JK", "name": "Perusahaan Gas Negara", "sector": "Energy"},
    {"ticker": "AKRA.JK", "name": "AKR Corporindo", "sector": "Energy"},
    {"ticker": "ENRG.JK", "name": "Energi Mega Persada", "sector": "Energy"},
    {"ticker": "BUMI.JK", "name": "Bumi Resources", "sector": "Energy"},
    {"ticker": "ITMG.JK", "name": "Indo Tambangraya Megah", "sector": "Energy"},
    {"ticker": "INDY.JK", "name": "Indika Energy", "sector": "Energy"},
    {"ticker": "HRUM.JK", "name": "Harum Energy", "sector": "Energy"},
    
    # Mineral, Nikel, Emas & Tambang
    {"ticker": "ANTM.JK", "name": "Aneka Tambang", "sector": "Basic Materials"},
    {"ticker": "INCO.JK", "name": "Vale Indonesia", "sector": "Basic Materials"},
    {"ticker": "MDKA.JK", "name": "Merdeka Copper Gold", "sector": "Basic Materials"},
    {"ticker": "MBMA.JK", "name": "Merdeka Battery Materials", "sector": "Basic Materials"},
    {"ticker": "AMMN.JK", "name": "Amman Mineral Internasional", "sector": "Basic Materials"},
    {"ticker": "NCKL.JK", "name": "Trimegah Bangun Persada", "sector": "Basic Materials"},
    {"ticker": "BRPT.JK", "name": "Barito Pacific", "sector": "Basic Materials"},
    {"ticker": "TPIA.JK", "name": "Chandra Asri Pacific", "sector": "Basic Materials"},
    {"ticker": "INKP.JK", "name": "Indah Kiat Pulp & Paper", "sector": "Basic Materials"},
    {"ticker": "TKIM.JK", "name": "Pabrik Kertas Tjiwi Kimia", "sector": "Basic Materials"},
    {"ticker": "PSAB.JK", "name": "J Resources Asia Pasifik", "sector": "Basic Materials"},
    
    # Konsumsi & Farmasi
    {"ticker": "ICBP.JK", "name": "Indofood CBP Sukses Makmur", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "INDF.JK", "name": "Indofood Sukses Makmur", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "MYOR.JK", "name": "Mayora Indah", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "KLBF.JK", "name": "Kalbe Farma", "sector": "Healthcare"},
    {"ticker": "SIDO.JK", "name": "Industri Jamu Dan Farmasi Sido Muncul", "sector": "Healthcare"},
    {"ticker": "CPIN.JK", "name": "Charoen Pokphand Indonesia", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "JPFA.JK", "name": "Japfa Comfeed Indonesia", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "UNVR.JK", "name": "Unilever Indonesia", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "AMRT.JK", "name": "Sumber Alfaria Trijaya", "sector": "Consumer Non-Cyclicals"},
    
    # Ritel & Konsumsi Siklikal
    {"ticker": "ACES.JK", "name": "Aspirasi Hidup Indonesia (Ace)", "sector": "Consumer Cyclicals"},
    {"ticker": "MAPI.JK", "name": "Mitra Adiperkasa", "sector": "Consumer Cyclicals"},
    {"ticker": "MAPA.JK", "name": "MAP Aktif Adiperkasa", "sector": "Consumer Cyclicals"},
    {"ticker": "ERAA.JK", "name": "Erajaya Swasembada", "sector": "Consumer Cyclicals"},
    
    # Telekomunikasi & Teknologi
    {"ticker": "TLKM.JK", "name": "Telkom Indonesia", "sector": "Telecommunication"},
    {"ticker": "ISAT.JK", "name": "Indosat Ooredoo Hutchison", "sector": "Telecommunication"},
    {"ticker": "EXCL.JK", "name": "XL Axiata", "sector": "Telecommunication"},
    {"ticker": "TOWR.JK", "name": "Sarana Menara Nusantara", "sector": "Telecommunication"},
    {"ticker": "TBIG.JK", "name": "Tower Bersama Infrastructure", "sector": "Telecommunication"},
    {"ticker": "GOTO.JK", "name": "GoTo Gojek Tokopedia", "sector": "Technology"},
    {"ticker": "EMTK.JK", "name": "Elang Mahkota Teknologi", "sector": "Technology"},
    
    # Properti & Infrastruktur
    {"ticker": "CTRA.JK", "name": "Ciputra Development", "sector": "Property"},
    {"ticker": "BSDE.JK", "name": "Bumi Serpong Damai", "sector": "Property"},
    {"ticker": "PWON.JK", "name": "Pakuwon Jati", "sector": "Property"},
    {"ticker": "SMRA.JK", "name": "Summarecon Agung", "sector": "Property"},
    {"ticker": "JSMR.JK", "name": "Jasa Marga", "sector": "Infrastructure"},
]

def get_universe():
    return IDX_STOCKS
