"""
===============================================================================
 ABD Elektrik Şebekesi - Ağ Kırılganlık Analizi
 (US Power Grid - Network Vulnerability Analysis)
===============================================================================
 Ders   : Çizge Teorisinde Ölçüm Parametreleri
 Konu   : Elektrik Şebekelerinde Kırılganlık ve Kritik Altyapı Analizi
 Veri   : power-US-Grid (networkrepository.com)
 Araçlar: Python 3.x, NetworkX, SciPy
===============================================================================
"""

import os
import argparse
import networkx as nx  # type: ignore
from scipy.io import mmread  # type: ignore


# =============================================================================
# 1. VERİ YÜKLEME FONKSİYONU
# =============================================================================
def load_power_grid(filepath: str) -> nx.Graph:
    """
    Elektrik şebekesi veri setini yükleyerek yönsüz (undirected) bir
    NetworkX Graph nesnesine dönüştürür.

    Desteklenen formatlar:
      - .mtx  → Matrix Market formatı (SciPy mmread ile okunur)
      - .edges / .txt → Standart kenar listesi formatı

    Parametreler
    ----------
    filepath : str
        Veri seti dosyasının yolu.

    Dönüş
    -----
    G : nx.Graph
        Yüklenen yönsüz çizge (graf).
    """

    # Dosyanın var olup olmadığını kontrol et
    if not os.path.isfile(filepath):
        raise FileNotFoundError(
            f"Veri seti dosyası bulunamadı: {filepath}\n"
            "Lütfen dosya yolunu kontrol edin."
        )

    # Dosya uzantısına göre uygun okuma yöntemini seç
    _, ext = os.path.splitext(filepath)

    if ext.lower() == ".mtx":
        # -----------------------------------------------------------------
        # Matrix Market formatı: SciPy ile seyrek matris olarak oku,
        # ardından NetworkX graf nesnesine dönüştür.
        # NOT: Windows'ta dosya yolunda Türkçe karakter varsa mmread
        #      hata verebilir; bu nedenle dosyayı önce open() ile açıp
        #      file handle olarak mmread'e veriyoruz.
        # -----------------------------------------------------------------
        with open(filepath, "rb") as f:
            sparse_matrix = mmread(f)
        G = nx.from_scipy_sparse_array(sparse_matrix)
        print(f"[BİLGİ] Matrix Market formatında yüklendi: {filepath}")
    else:
        # -----------------------------------------------------------------
        # Standart kenar listesi formatı (.edges, .txt vb.):
        # Her satırda "düğüm1 düğüm2" çiftleri beklenir.
        # Yorum satırları '#' veya '%' ile başlar.
        # -----------------------------------------------------------------
        G = nx.read_edgelist(filepath, comments="%", nodetype=int)
        print(f"[BİLGİ] Kenar listesi formatında yüklendi: {filepath}")

    return G


# =============================================================================
# 2. TEMEL AĞ METRİKLERİNİ YAZDIRAN FONKSİYON
# =============================================================================
def print_network_summary(G: nx.Graph) -> None:
    """
    Çizgenin temel yapısal özelliklerini ekrana yazdırır.

    Bu metrikler, ağın genel büyüklüğünü ve bağlantı yapısını
    anlamak için kullanılır.

    Yazdırılan Bilgiler:
      - Düğüm sayısı  (trafo/dağıtım merkezlerini temsil eder)
      - Kenar sayısı   (enerji iletim hatlarını temsil eder)
      - Ortalama derece (her düğümün ortalama bağlantı sayısı)
      - Yoğunluk       (ağın ne kadar sıkı bağlı olduğu)
      - Bağlı bileşen sayısı (ağdaki izole alt gruplar)
    """

    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    avg_degree = (2.0 * num_edges) / num_nodes if num_nodes > 0 else 0
    density = nx.density(G)
    num_components = nx.number_connected_components(G)

    print("\n" + "=" * 65)
    print("  ABD ELEKTRİK ŞEBEKESİ — TEMEL AĞ METRİKLERİ")
    print("=" * 65)
    print(f"  Düğüm sayısı (Trafo/Dağıtım Merkezleri) : {num_nodes:>6,}")
    print(f"  Kenar sayısı (Enerji İletim Hatları)     : {num_edges:>6,}")
    print(f"  Ortalama Derece (Avg. Degree)             : {avg_degree:>9.4f}")
    print(f"  Ağ Yoğunluğu (Density)                   : {density:>9.6f}")
    print(f"  Bağlı Bileşen Sayısı (Connected Comp.)   : {num_components:>6}")
    print("=" * 65)


# =============================================================================
# 3. ARASINALIK MERKEZİLİĞİ (BETWEENNESS CENTRALITY) HESAPLAMA
# =============================================================================
def calculate_betweenness_centrality(G: nx.Graph) -> dict:
    """
    Tüm düğümler için Arasınalık Merkeziliği (Betweenness Centrality)
    değerini hesaplar.

    Arasınalık Merkeziliği Nedir?
    ----------------------------
    Bir düğümün, ağdaki diğer tüm düğüm çiftleri arasındaki en kısa
    yollar üzerinde ne sıklıkla bulunduğunu ölçer. Yüksek değere sahip
    düğümler, ağdaki bilgi/enerji akışı için kritik öneme sahiptir.

    Elektrik şebekesi bağlamında, yüksek arasınalık merkeziliğine sahip
    düğümler, arızalandığında ağın büyük bölümünü etkileyen kritik
    trafo ve dağıtım merkezlerini temsil eder.

    Parametreler
    ----------
    G : nx.Graph
        Analiz edilecek çizge.

    Dönüş
    -----
    bc : dict
        {düğüm_id: arasınalık_değeri} sözlüğü.
    """

    print("\n[HESAPLAMA] Arasınalık Merkeziliği hesaplanıyor...")
    print("             (Bu işlem büyük ağlar için birkaç dakika sürebilir)\n")

    bc = nx.betweenness_centrality(G, normalized=True)

    print("[TAMAM] Arasınalık Merkeziliği hesaplaması tamamlandı.")
    return bc


# =============================================================================
# 4. EN KRİTİK 10 DÜĞÜMÜ LİSTELEME
# =============================================================================
def print_top_critical_nodes(bc: dict, top_n: int = 10) -> list:
    """
    Arasınalık Merkeziliği en yüksek olan düğümleri sıralar ve ekrana
    yazdırır. Bu düğümler ağın en kritik noktalarıdır.

    Parametreler
    ----------
    bc : dict
        Arasınalık merkeziliği sözlüğü.
    top_n : int
        Listelenecek düğüm sayısı (varsayılan: 10).

    Dönüş
    -----
    top_nodes : list of tuple
        [(düğüm_id, bc_değeri), ...] şeklinde sıralı liste.
    """

    # Arasınalık merkeziliği değerine göre büyükten küçüğe sırala
    sorted_nodes: list[tuple[int, float]] = sorted(
        bc.items(), key=lambda x: x[1], reverse=True
    )
    top_nodes = sorted_nodes[:top_n]  # type: ignore[index]

    print("\n" + "=" * 65)
    print(f"  EN KRİTİK {top_n} DÜĞÜM (Arasınalık Merkeziliğine Göre)")
    print("=" * 65)
    print(f"  {'Sıra':<6} {'Düğüm ID':<12} {'Betweenness Centrality':<25}")
    print("-" * 65)

    for rank, (node, value) in enumerate(top_nodes, start=1):
        print(f"  {rank:<6} {node:<12} {value:<25.10f}")

    print("=" * 65)

    return top_nodes


# =============================================================================
# 5. EN BÜYÜK BAĞLI BİLEŞEN (LCC) BOYUTU HESAPLAMA
# =============================================================================
def calculate_lcc_size(G: nx.Graph) -> int:
    """
    Ağdaki En Büyük Bağlı Bileşenin (Largest Connected Component - LCC)
    düğüm sayısını hesaplar ve döndürür.

    Bu metrik neden önemli?
    -----------------------
    Bir elektrik şebekesinde düğüm veya kenar arızası simüle edildiğinde,
    ağ parçalara ayrılabilir. LCC boyutundaki düşüş, şebekenin ne kadar
    kırılgan olduğunu gösterir.

    İlerideki analizlerde, düğüm çıkarma (node removal) senaryolarında
    LCC boyutu değişimini takip ederek şebeke dayanıklılığını ölçeceğiz.

    Parametreler
    ----------
    G : nx.Graph
        Analiz edilecek çizge.

    Dönüş
    -----
    lcc_size : int
        En büyük bağlı bileşendeki düğüm sayısı.
    """

    if G.number_of_nodes() == 0:
        return 0

    # Bağlı bileşenleri büyüklüğüne göre sırala (en büyük ilk sırada)
    largest_component = max(nx.connected_components(G), key=len)
    lcc_size = len(largest_component)

    print("\n" + "=" * 65)
    print("  EN BÜYÜK BAĞLI BİLEŞEN (LCC) ANALİZİ")
    print("=" * 65)
    print(f"  Toplam düğüm sayısı              : {G.number_of_nodes():>6,}")
    print(f"  LCC düğüm sayısı                 : {lcc_size:>6,}")
    print(f"  LCC oranı (LCC / Toplam)          : {lcc_size / G.number_of_nodes():>9.4f}")
    print("=" * 65)

    return lcc_size


# =============================================================================
# ANA PROGRAM (MAIN)
# =============================================================================
def main():
    """
    Programın ana akış fonksiyonu. Tüm analiz adımlarını sırasıyla çalıştırır.
    """
    print("╔" + "═" * 63 + "╗")
    print("║  ABD Elektrik Şebekesi – Kırılganlık Analizi                 ║")
    print("║  Ders: Çizge Teorisinde Ölçüm Parametreleri                  ║")
    print("╚" + "═" * 63 + "╝")

    # --- CLI (Terminal Argümanı) ENTEGRASYONU ---
    parser = argparse.ArgumentParser(description="Elektrik Şebekesi Kırılganlık Analizi")
    
    # Varsayılan dosya yolunu yeni klasör yapısına göre (src -> data) dinamik hesapla
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_data_path = os.path.join(base_dir, "data", "power-US-Grid", "power-US-Grid.mtx")
    
    parser.add_argument(
        "--data", 
        type=str, 
        default=default_data_path,
        help="Veri setinin (.mtx) dosya yolu"
    )
    args = parser.parse_args()

    # --- Adım 1: Veri Setini Yükle ---
    G = load_power_grid(args.data)

    # --- Adım 2: Temel Ağ Metriklerini Yazdır ---
    print_network_summary(G)

    # --- Adım 3: Arasındalık Merkeziliğini Hesapla ---
    bc = calculate_betweenness_centrality(G)

    # --- Adım 4: En Kritik 10 Düğümü Listele ---
    top_nodes = print_top_critical_nodes(bc, top_n=10)

    # --- Adım 5: En Büyük Bağlı Bileşen Boyutunu Hesapla ---
    lcc_size = calculate_lcc_size(G)

    # --- Özet ---
    print("\n" + "=" * 65)
    print("  ANALİZ TAMAMLANDI")
    print("=" * 65)
    print("  ✓ Ağ yapısı başarıyla yüklendi ve analiz edildi.")
    print("  ✓ Arasındalık Merkeziliği hesaplandı.")
    print(f"  ✓ En kritik düğüm: Düğüm {top_nodes[0][0]} (BC = {top_nodes[0][1]:.10f})")
    print(f"  ✓ LCC boyutu: {lcc_size:,} düğüm")
    print("=" * 65)
    print("\n  [SONRAKİ ADIM] Düğüm çıkarma simülasyonu ile")
    print("  kırılganlık analizi yapılacaktır.\n")


# =============================================================================
# Programı çalıştır
# =============================================================================
if __name__ == "__main__":
    main()
