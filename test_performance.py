#!/usr/bin/env python3
"""
Performance-Testing für Mail AI Sorter.

Testet die Performance-Verbesserungen durch Caching und Connection Pooling.
"""

import json
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_stats_performance():
    """Teste Stats-Performance mit und ohne Cache."""
    print("=" * 60)
    print("📊 Stats Performance Test")
    print("=" * 60)

    from services.stats_service import get_stats, get_detailed_stats

    # Erster Aufruf (kalt)
    print("\n1. Erster Aufruf (Cache kalt):")
    start = time.time()
    stats = get_stats()
    elapsed_cold = time.time() - start
    print(f"   Zeit: {elapsed_cold:.2f}s")
    print(f"   Ergebnis: {stats.get('total', 0)} Emails")

    # Zweiter Aufruf (warm)
    print("\n2. Zweiter Aufruf (Cache warm):")
    start = time.time()
    stats = get_stats()
    elapsed_warm = time.time() - start
    print(f"   Zeit: {elapsed_warm:.2f}s")
    print(f"   Verbesserung: {elapsed_cold/elapsed_warm:.1f}x schneller")

    # Detaillierte Stats
    print("\n3. Detaillierte Stats (30 Tage):")
    start = time.time()
    detailed = get_detailed_stats("30")
    elapsed_detailed = time.time() - start
    print(f"   Zeit: {elapsed_detailed:.2f}s")
    print(f"   Top Sender: {len(detailed.get('top_senders', []))}")

    return {
        "stats_cold": elapsed_cold,
        "stats_warm": elapsed_warm,
        "detailed": elapsed_detailed,
    }


def test_imap_performance():
    """Teste IMAP-Performance mit Connection Pooling."""
    print("\n" + "=" * 60)
    print("📧 IMAP Performance Test")
    print("=" * 60)

    try:
        from config_service import load_config, inject_account_secret
        from services.imap_service import list_folder_emails

        cfg = load_config()
        accounts = cfg.get("accounts", [])

        if not accounts:
            print("❌ Keine Accounts konfiguriert")
            return {}

        account = inject_account_secret(accounts[0])
        account_name = account.get("name", "Unknown")

        print(f"\n📮 Teste Account: {account_name}")

        # Erste Abfrage
        print("\n1. Erste Abfrage (Connection kalt):")
        start = time.time()
        emails, total = list_folder_emails(account, "INBOX", 1, 20)
        elapsed_cold = time.time() - start
        print(f"   Zeit: {elapsed_cold:.2f}s")
        print(f"   Ergebnis: {len(emails)} von {total} Emails")

        # Zweite Abfrage (sollte Connection Pool nutzen)
        print("\n2. Zweite Abfrage (Connection warm):")
        start = time.time()
        emails2, total2 = list_folder_emails(account, "INBOX", 1, 20)
        elapsed_warm = time.time() - start
        print(f"   Zeit: {elapsed_warm:.2f}s")
        print(f"   Verbesserung: {elapsed_cold/elapsed_warm:.1f}x schneller")

        # Dritte Abfrage
        print("\n3. Dritte Abfrage (Pool Effect):")
        start = time.time()
        emails3, total3 = list_folder_emails(account, "INBOX", 2, 20)
        elapsed_third = time.time() - start
        print(f"   Zeit: {elapsed_third:.2f}s")
        print(f"   Verbesserung: {elapsed_cold/elapsed_third:.1}x schneller als erste Abfrage")

        return {
            "imap_cold": elapsed_cold,
            "imap_warm": elapsed_warm,
            "imap_third": elapsed_third,
        }

    except Exception as e:
        print(f"❌ IMAP Test fehlgeschlagen: {e}")
        return {}


def test_cache_performance():
    """Teste Cache-Performance."""
    print("\n" + "=" * 60)
    print("💾 Cache Performance Test")
    print("=" * 60)

    from services.cache_service import _cache_manager

    print("\n1. Cache Basics:")
    print(f"   Cache-Size: {len(_cache_manager._cache)} Einträge")

    # Test Cache Set/Get
    print("\n2. Cache Set/Get Test:")
    start = time.time()
    for i in range(1000):
        _cache_manager.set(f"test_key_{i}", f"test_value_{i}", ttl=60)
    set_time = time.time() - start
    print(f"   1000x Set: {set_time:.3f}s ({1000/set_time:.0f} ops/s)")

    start = time.time()
    for i in range(1000):
        value = _cache_manager.get(f"test_key_{i}")
    get_time = time.time() - start
    print(f"   1000x Get: {get_time:.3f}s ({1000/get_time:.0f} ops/s)")

    # Cleanup
    print("\n3. Cache Cleanup:")
    _cache_manager.invalidate("test_key")
    print(f"   Cache aufgeräumt")

    return {
        "cache_set_ops": 1000 / set_time,
        "cache_get_ops": 1000 / get_time,
    }


def generate_performance_report(stats_results, imap_results, cache_results):
    """Generiere Performance-Report."""
    print("\n" + "=" * 60)
    print("📈 PERFORMANCE REPORT")
    print("=" * 60)

    report = {
        "timestamp": time.time(),
        "results": {
            "stats": stats_results,
            "imap": imap_results,
            "cache": cache_results,
        },
    }

    print("\n✅ Stats Performance:")
    if stats_results:
        cold = stats_results.get("stats_cold", 0)
        warm = stats_results.get("stats_warm", 0)
        if warm > 0:
            print(f"   Cache-Verbesserung: {cold/warm:.1f}x")
        print(f"   Kalt: {cold:.2f}s | Warm: {warm:.2f}s")

    print("\n✅ IMAP Performance:")
    if imap_results:
        cold = imap_results.get("imap_cold", 0)
        warm = imap_results.get("imap_warm", 0)
        third = imap_results.get("imap_third", 0)
        if warm > 0:
            print(f"   Connection Pool: {cold/warm:.1f}x schneller")
        if third > 0:
            print(f"   Nach 3. Abfrage: {cold/third:.1f}x schneller")

    print("\n✅ Cache Performance:")
    if cache_results:
        set_ops = cache_results.get("cache_set_ops", 0)
        get_ops = cache_results.get("cache_get_ops", 0)
        print(f"   Set: {set_ops:.0f} ops/s")
        print(f"   Get: {get_ops:.0f} ops/s")

    # Empfehlungen
    print("\n💡 Empfehlungen:")
    if stats_results and stats_results.get("stats_warm", 0) < 0.1:
        print("   ✅ Stats-Caching funktioniert gut!")

    if imap_results:
        improvement = imap_results.get("imap_cold", 0) / max(imap_results.get("imap_warm", 1), 0.1)
        if improvement > 1.5:
            print("   ✅ Connection Pooling funktioniert gut!")
        elif improvement < 1.2:
            print("   ⚠️  Connection Pooling könnte verbessert werden")

    # Speichern
    report_path = Path(__file__).parent / "performance_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Report gespeichert: {report_path}")

    return report


def main():
    """Hauptfunktion."""
    print("🚀 Starte Performance-Tests...")
    print()

    try:
        # Stats Test
        stats_results = test_stats_performance()

        # IMAP Test
        imap_results = test_imap_performance()

        # Cache Test
        cache_results = test_cache_performance()

        # Report
        report = generate_performance_report(stats_results, imap_results, cache_results)

        print("\n" + "=" * 60)
        print("✅ Performance-Tests abgeschlossen!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Test fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())