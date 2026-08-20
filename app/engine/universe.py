# Daftar Saham Likuid IDX (Indeks Kompas100 Resmi BEI / High Liquidity Universe)
# Menghindari saham gorengan illiquid yang berisiko manipulasi

IDX_STOCKS = [
    # Perbankan & Finansial (15 Saham)
    {"ticker": "BBCA.JK", "name": "Bank Central Asia", "sector": "Finance"},
    {"ticker": "BBRI.JK", "name": "Bank Rakyat Indonesia", "sector": "Finance"},
    {"ticker": "BMRI.JK", "name": "Bank Mandiri", "sector": "Finance"},
    {"ticker": "BBNI.JK", "name": "Bank Negara Indonesia", "sector": "Finance"},
    {"ticker": "BRIS.JK", "name": "Bank Syariah Indonesia", "sector": "Finance"},
    {"ticker": "BBTN.JK", "name": "Bank Tabungan Negara", "sector": "Finance"},
    {"ticker": "ARTO.JK", "name": "Bank Jago", "sector": "Finance"},
    {"ticker": "BDMN.JK", "name": "Bank Danamon Indonesia", "sector": "Finance"},
    {"ticker": "BNGA.JK", "name": "Bank CIMB Niaga", "sector": "Finance"},
    {"ticker": "BFIN.JK", "name": "BFI Finance Indonesia", "sector": "Finance"},
    {"ticker": "BJBR.JK", "name": "Bank Pembangunan Daerah BJB", "sector": "Finance"},
    {"ticker": "BJTM.JK", "name": "Bank Jatim", "sector": "Finance"},
    {"ticker": "PNBN.JK", "name": "Bank Pan Indonesia", "sector": "Finance"},
    {"ticker": "BBHI.JK", "name": "Allo Bank Indonesia", "sector": "Finance"},
    {"ticker": "BTPS.JK", "name": "Bank BTPN Syariah", "sector": "Finance"},
    
    # Otomotif, Alat Berat & Industri (8 Saham)
    {"ticker": "ASII.JK", "name": "Astra International", "sector": "Industrial"},
    {"ticker": "AUTO.JK", "name": "Astra Otoparts", "sector": "Industrial"},
    {"ticker": "UNTR.JK", "name": "United Tractors", "sector": "Industrial"},
    {"ticker": "HEXA.JK", "name": "Hexindo Adiperkasa", "sector": "Industrial"},
    {"ticker": "GJTL.JK", "name": "Gajah Tunggal", "sector": "Industrial"},
    {"ticker": "SMSM.JK", "name": "Selamat Sempurna", "sector": "Industrial"},
    {"ticker": "ASSA.JK", "name": "Adi Sarana Armada", "sector": "Industrial"},
    {"ticker": "MARK.JK", "name": "Mark Dynamics Indonesia", "sector": "Industrial"},
    
    # Energi, Batu Bara, Migas & Renewable (15 Saham)
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
    {"ticker": "PGEO.JK", "name": "Pertamina Geothermal Energy", "sector": "Energy"},
    {"ticker": "BREN.JK", "name": "Barito Renewables Energy", "sector": "Energy"},
    {"ticker": "DOID.JK", "name": "Delta Dunia Makmur", "sector": "Energy"},
    {"ticker": "TOBA.JK", "name": "TBS Energi Utama", "sector": "Energy"},
    {"ticker": "ELSA.JK", "name": "Elnusa", "sector": "Energy"},
    
    # Mineral, Tambang, Logam & Bahan Baku (15 Saham)
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
    {"ticker": "SMGR.JK", "name": "Semen Indonesia", "sector": "Basic Materials"},
    {"ticker": "INTP.JK", "name": "Indocement Tunggal Prakarsa", "sector": "Basic Materials"},
    {"ticker": "ESSA.JK", "name": "Essa Industries Indonesia", "sector": "Basic Materials"},
    {"ticker": "AVIA.JK", "name": "Avia Avian", "sector": "Basic Materials"},
    {"ticker": "PSAB.JK", "name": "J Resources Asia Pasifik", "sector": "Basic Materials"},
    
    # Konsumsi, Makanan, Minuman & Farmasi / Kesehatan (18 Saham)
    {"ticker": "ICBP.JK", "name": "Indofood CBP Sukses Makmur", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "INDF.JK", "name": "Indofood Sukses Makmur", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "MYOR.JK", "name": "Mayora Indah", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "CPIN.JK", "name": "Charoen Pokphand Indonesia", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "JPFA.JK", "name": "Japfa Comfeed Indonesia", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "UNVR.JK", "name": "Unilever Indonesia", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "AMRT.JK", "name": "Sumber Alfaria Trijaya", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "MIDI.JK", "name": "Midi Utama Indonesia", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "CMRY.JK", "name": "Cisarua Mountain Dairy", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "ULTJ.JK", "name": "Ultra Jaya Milk Industry", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "CLEO.JK", "name": "Sariguna Primatirta", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "ROTI.JK", "name": "Nippon Indosari Corpindo", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "TAPG.JK", "name": "Triputra Agro Persada", "sector": "Consumer Non-Cyclicals"},
    {"ticker": "KLBF.JK", "name": "Kalbe Farma", "sector": "Healthcare"},
    {"ticker": "SIDO.JK", "name": "Industri Jamu Dan Farmasi Sido Muncul", "sector": "Healthcare"},
    {"ticker": "HEAL.JK", "name": "Medikaloka Hermina", "sector": "Healthcare"},
    {"ticker": "SILO.JK", "name": "Siloam International Hospitals", "sector": "Healthcare"},
    {"ticker": "MIKA.JK", "name": "Mitra Keluarga Karyasehat", "sector": "Healthcare"},
    
    # Ritel, Lifestyle & Konsumsi Siklikal (6 Saham)
    {"ticker": "ACES.JK", "name": "Aspirasi Hidup Indonesia (Ace)", "sector": "Consumer Cyclicals"},
    {"ticker": "MAPI.JK", "name": "Mitra Adiperkasa", "sector": "Consumer Cyclicals"},
    {"ticker": "MAPA.JK", "name": "MAP Aktif Adiperkasa", "sector": "Consumer Cyclicals"},
    {"ticker": "ERAA.JK", "name": "Erajaya Swasembada", "sector": "Consumer Cyclicals"},
    {"ticker": "RALS.JK", "name": "Ramayana Lestari Sentosa", "sector": "Consumer Cyclicals"},
    {"ticker": "LPPF.JK", "name": "Matahari Department Store", "sector": "Consumer Cyclicals"},
    
    # Telekomunikasi, Teknologi & Media (10 Saham)
    {"ticker": "TLKM.JK", "name": "Telkom Indonesia", "sector": "Telecommunication"},
    {"ticker": "ISAT.JK", "name": "Indosat Ooredoo Hutchison", "sector": "Telecommunication"},
    {"ticker": "EXCL.JK", "name": "XL Axiata", "sector": "Telecommunication"},
    {"ticker": "TOWR.JK", "name": "Sarana Menara Nusantara", "sector": "Telecommunication"},
    {"ticker": "TBIG.JK", "name": "Tower Bersama Infrastructure", "sector": "Telecommunication"},
    {"ticker": "MTEL.JK", "name": "Dayamitra Telekomunikasi", "sector": "Telecommunication"},
    {"ticker": "GOTO.JK", "name": "GoTo Gojek Tokopedia", "sector": "Technology"},
    {"ticker": "BUKA.JK", "name": "Bukalapak.com", "sector": "Technology"},
    {"ticker": "EMTK.JK", "name": "Elang Mahkota Teknologi", "sector": "Technology"},
    {"ticker": "SCMA.JK", "name": "Surya Citra Media", "sector": "Technology"},
    
    # Properti, Real Estate & Konstruksi (9 Saham)
    {"ticker": "CTRA.JK", "name": "Ciputra Development", "sector": "Property"},
    {"ticker": "BSDE.JK", "name": "Bumi Serpong Damai", "sector": "Property"},
    {"ticker": "PWON.JK", "name": "Pakuwon Jati", "sector": "Property"},
    {"ticker": "SMRA.JK", "name": "Summarecon Agung", "sector": "Property"},
    {"ticker": "SSIA.JK", "name": "Surya Semesta Internusa", "sector": "Property"},
    {"ticker": "KIJA.JK", "name": "Kawasan Industri Jababeka", "sector": "Property"},
    {"ticker": "PTPP.JK", "name": "PP (Persero)", "sector": "Property"},
    {"ticker": "ADHI.JK", "name": "Adhi Karya (Persero)", "sector": "Property"},
    {"ticker": "WIKA.JK", "name": "Wijaya Karya (Persero)", "sector": "Property"},
    
    # Infrastruktur, Logistik & Pelayaran (5 Saham)
    {"ticker": "JSMR.JK", "name": "Jasa Marga", "sector": "Infrastructure"},
    {"ticker": "SMDR.JK", "name": "Samudera Indonesia", "sector": "Infrastructure"},
    {"ticker": "TMAS.JK", "name": "Temas", "sector": "Infrastructure"},
    {"ticker": "HAIS.JK", "name": "Hasnur Internasional Shipping", "sector": "Infrastructure"},
    {"ticker": "IPCC.JK", "name": "Indonesia Kendaraan Terminal", "sector": "Infrastructure"},
]

def get_universe():
    return IDX_STOCKS
