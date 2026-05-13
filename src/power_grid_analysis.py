"""
===============================================================================
 ABD Elektrik Şebekesi - Ağ Kırılganlık Analizi
 (US Power Grid - Network Vulnerability Analysis)
===============================================================================
 Ders   : Çizge Teorisinde Ölçüm Parametreleri
 Konu   : Elektrik Şebekelerinde Kırılganlık ve Kritik Altyapı Analizi
 Veri   : power-US-Grid (networkrepository.com)
 Araçlar: Python 3.x, NetworkX, SciPy, Matplotlib
===============================================================================
"""

import os
import copy
import random
import argparse
import networkx as nx  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
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
# 6. HEDEFLİ SALDIRI SİMÜLASYONU (TARGETED ATTACK)
# =============================================================================
def simulate_targeted_attack(G: nx.Graph, bc: dict,
                             max_removal_pct: int = 20) -> list:
    """
    Arasındalık Merkeziliği (Betweenness Centrality) skorlarına göre
    en kritik düğümlerden başlayarak ağdan düğüm çıkarır ve her adımda
    LCC oranını kaydeder.

    Bu simülasyon, bir saldırganın şebekenin en kritik noktalarını
    hedef aldığı senaryoyu modellemektedir.

    Parametreler
    ----------
    G : nx.Graph
        Orijinal çizge (kopyası alınır, orijinal bozulmaz).
    bc : dict
        Önceden hesaplanmış Arasındalık Merkeziliği sözlüğü.
    max_removal_pct : int
        Silinecek maksimum düğüm yüzdesi (varsayılan: 20).

    Dönüş
    -----
    results : list of tuple
        [(yüzde, lcc_oranı), ...] şeklinde her adımın kaydı.
    """

    print("\n[SİMÜLASYON] Hedefli Saldırı simülasyonu başlatılıyor...")

    G_copy = copy.deepcopy(G)
    total_nodes = G.number_of_nodes()

    # Düğümleri BC skoruna göre büyükten küçüğe sırala
    sorted_nodes = sorted(bc.items(), key=lambda x: x[1], reverse=True)
    sorted_node_ids = [node for node, _ in sorted_nodes]

    # Başlangıç durumu: %0 silindi, LCC oranı hesapla
    initial_lcc = len(max(nx.connected_components(G_copy), key=len))
    results = [(0, initial_lcc / total_nodes)]

    # %1, %2, ... %max_removal_pct adımlarında düğüm sil
    step_size = max(1, total_nodes // 100)  # Her %1'lik adım

    for pct in range(1, max_removal_pct + 1):
        target_removal_count = int(total_nodes * pct / 100)

        # Şimdiye kadar silinmiş düğüm sayısını hesapla
        already_removed = total_nodes - G_copy.number_of_nodes()
        to_remove = target_removal_count - already_removed

        if to_remove > 0:
            # Sıralı listeden hâlâ grafta olan düğümleri sil
            removed = 0
            for node_id in sorted_node_ids:
                if removed >= to_remove:
                    break
                if G_copy.has_node(node_id):
                    G_copy.remove_node(node_id)
                    removed += 1

        # LCC oranını hesapla
        if G_copy.number_of_nodes() > 0:
            current_lcc = len(max(nx.connected_components(G_copy), key=len))
            lcc_ratio = current_lcc / total_nodes
        else:
            lcc_ratio = 0.0

        results.append((pct, lcc_ratio))
        print(f"  [%{pct:>2}] Silinen: {target_removal_count:>5} düğüm | "
              f"LCC Oranı: {lcc_ratio:.4f}")

    print("[TAMAM] Hedefli Saldırı simülasyonu tamamlandı.")
    return results


# =============================================================================
# 7. RASTGELE ARIZA SİMÜLASYONU (RANDOM FAILURE)
# =============================================================================
def simulate_random_failure(G: nx.Graph, max_removal_pct: int = 20,
                            num_trials: int = 3, seed: int = 42) -> list:
    """
    Ağdan rastgele düğümler çıkararak her adımda LCC oranını kaydeder.
    Daha tutarlı sonuçlar elde etmek için simülasyonu birden çok kez
    tekrarlayıp ortalama alır.

    Bu simülasyon, doğal afet veya ekipman yaşlanması gibi rastgele
    arıza senaryolarını modellemektedir.

    Parametreler
    ----------
    G : nx.Graph
        Orijinal çizge (kopyası alınır, orijinal bozulmaz).
    max_removal_pct : int
        Silinecek maksimum düğüm yüzdesi (varsayılan: 20).
    num_trials : int
        Tekrar sayısı (varsayılan: 3).
    seed : int
        Rastgelelik tohumu (tekrarlanabilirlik için, varsayılan: 42).

    Dönüş
    -----
    avg_results : list of tuple
        [(yüzde, ortalama_lcc_oranı), ...] şeklinde her adımın kaydı.
    """

    print(f"\n[SİMÜLASYON] Rastgele Arıza simülasyonu başlatılıyor "
          f"({num_trials} deneme)...")

    total_nodes = G.number_of_nodes()
    all_nodes = list(G.nodes())

    # Her deneme için sonuçları topla
    all_trial_ratios = {pct: [] for pct in range(0, max_removal_pct + 1)}

    rng = random.Random(seed)

    for trial in range(num_trials):
        G_copy = copy.deepcopy(G)
        # Rastgele sıralama oluştur
        shuffled_nodes = all_nodes[:]
        rng.shuffle(shuffled_nodes)

        # Başlangıç LCC oranı
        initial_lcc = len(max(nx.connected_components(G_copy), key=len))
        all_trial_ratios[0].append(initial_lcc / total_nodes)

        for pct in range(1, max_removal_pct + 1):
            target_removal_count = int(total_nodes * pct / 100)
            already_removed = total_nodes - G_copy.number_of_nodes()
            to_remove = target_removal_count - already_removed

            if to_remove > 0:
                removed = 0
                for node_id in shuffled_nodes:
                    if removed >= to_remove:
                        break
                    if G_copy.has_node(node_id):
                        G_copy.remove_node(node_id)
                        removed += 1

            if G_copy.number_of_nodes() > 0:
                current_lcc = len(max(nx.connected_components(G_copy), key=len))
                lcc_ratio = current_lcc / total_nodes
            else:
                lcc_ratio = 0.0

            all_trial_ratios[pct].append(lcc_ratio)

        print(f"  Deneme {trial + 1}/{num_trials} tamamlandı.")

    # Ortalamaları hesapla
    avg_results = []
    for pct in range(0, max_removal_pct + 1):
        avg_ratio = sum(all_trial_ratios[pct]) / len(all_trial_ratios[pct])
        avg_results.append((pct, avg_ratio))

    # Ortalama sonuçları yazdır
    print("\n  Rastgele Arıza — Ortalama Sonuçlar:")
    for pct, ratio in avg_results:
        if pct > 0:
            print(f"  [%{pct:>2}] Ortalama LCC Oranı: {ratio:.4f}")

    print("[TAMAM] Rastgele Arıza simülasyonu tamamlandı.")
    return avg_results


# =============================================================================
# 8. KIRILGANLIK EĞRİSİ GÖRSELLEŞTİRME (VULNERABILITY CURVE)
# =============================================================================
def plot_vulnerability_curve(targeted_results: list,
                             random_results: list,
                             save_path: str = None) -> None:
    """
    Hedefli Saldırı ve Rastgele Arıza simülasyonlarının sonuçlarını
    tek bir çizgi grafiğinde (line plot) karşılaştırmalı olarak çizer.

    Parametreler
    ----------
    targeted_results : list of tuple
        Hedefli saldırı sonuçları: [(yüzde, lcc_oranı), ...].
    random_results : list of tuple
        Rastgele arıza sonuçları: [(yüzde, lcc_oranı), ...].
    save_path : str, optional
        Grafiğin kaydedileceği dosya yolu. None ise kaydetmez.
    """

    print("\n[GÖRSELLEŞTİRME] Kırılganlık eğrisi oluşturuluyor...")

    # Verileri X ve Y eksenlerine ayır
    targeted_x = [r[0] for r in targeted_results]
    targeted_y = [r[1] for r in targeted_results]

    random_x = [r[0] for r in random_results]
    random_y = [r[1] for r in random_results]

    # Grafik oluştur
    plt.figure(figsize=(10, 6))

    plt.plot(targeted_x, targeted_y, color="red", linewidth=2.0,
             marker="o", markersize=4, label="Hedefli Saldırı (Targeted Attack)")
    plt.plot(random_x, random_y, color="blue", linewidth=2.0,
             marker="s", markersize=4, label="Rastgele Arıza (Random Failure)")

    # Eksen etiketleri ve başlık
    plt.xlabel("Devre Dışı Bırakılan Trafo Yüzdesi (%)", fontsize=12)
    plt.ylabel("Şebeke Bütünlük Oranı (LCC)", fontsize=12)
    plt.title("ABD Elektrik Şebekesi — Kırılganlık Analizi\n"
              "(Hedefli Saldırı vs. Rastgele Arıza)", fontsize=14)

    # Izgara ve gösterge
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend(loc="best", fontsize=11)

    # Eksen aralıkları
    plt.xlim(0, max(targeted_x))
    plt.ylim(0, 1.05)

    plt.tight_layout()

    # Dosyaya kaydet
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"[TAMAM] Grafik kaydedildi: {save_path}")

    # Ekranda göster
    plt.show()

    print("[TAMAM] Görselleştirme tamamlandı.")


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

    # --- Özet (Faz 1) ---
    print("\n" + "=" * 65)
    print("  FAZ 1 — ANALİZ TAMAMLANDI")
    print("=" * 65)
    print("  ✓ Ağ yapısı başarıyla yüklendi ve analiz edildi.")
    print("  ✓ Arasındalık Merkeziliği hesaplandı.")
    print(f"  ✓ En kritik düğüm: Düğüm {top_nodes[0][0]} (BC = {top_nodes[0][1]:.10f})")
    print(f"  ✓ LCC boyutu: {lcc_size:,} düğüm")
    print("=" * 65)

    # =================================================================
    # FAZ 2 — ARIZA SİMÜLASYONU VE GÖRSELLEŞTİRME
    # =================================================================
    print("\n" + "╔" + "═" * 63 + "╗")
    print("║  FAZ 2 — Arıza Simülasyonu & Kırılganlık Görselleştirmesi    ║")
    print("╚" + "═" * 63 + "╝")

    # --- Adım 6: Hedefli Saldırı Simülasyonu ---
    targeted_results = simulate_targeted_attack(G, bc, max_removal_pct=20)

    # --- Adım 7: Rastgele Arıza Simülasyonu ---
    random_results = simulate_random_failure(G, max_removal_pct=20,
                                             num_trials=3, seed=42)

    # --- Adım 8: Kırılganlık Eğrisi Görselleştirmesi ---
    save_path = os.path.join(base_dir, "docs", "vulnerability_curve.png")
    plot_vulnerability_curve(targeted_results, random_results,
                             save_path=save_path)

    # --- Son Özet ---
    print("\n" + "=" * 65)
    print("  TÜM ANALİZLER TAMAMLANDI")
    print("=" * 65)
    print("  ✓ Faz 1: Ağ metrikleri ve kritik düğüm analizi")
    print("  ✓ Faz 2: Hedefli saldırı simülasyonu")
    print("  ✓ Faz 2: Rastgele arıza simülasyonu")
    print(f"  ✓ Kırılganlık eğrisi kaydedildi: docs/vulnerability_curve.png")
    print("=" * 65 + "\n")


# =============================================================================
# Programı çalıştır
# =============================================================================
if __name__ == "__main__":
    main()
