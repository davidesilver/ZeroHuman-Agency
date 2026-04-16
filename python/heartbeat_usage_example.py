"""
Esempio di utilizzo del sistema Heartbeat con rate limiting disabilitato.

Questo esempio mostra come il sistema heartbeat funziona senza limitazioni,
permettendo chiamate illimitate come richiesto.
"""

import asyncio
import time
from src.content_engine.utils.heartbeat import (
    record_agent_heartbeat,
    get_cached_heartbeat,
    get_all_cached_heartbeats,
    get_cache_stats,
    set_rate_limiting,
)


async def example_unlimited_heartbeats():
    """Esempio di utilizzo con rate limiting disabilitato (default)."""

    print("🚀 Esempio: Heartbeat illimitati (rate limiting disabilitato)")
    print("=" * 60)

    # Verifica stato rate limiting (dovrebbe essere disabilitato)
    stats = get_cache_stats()
    print(f"📊 Rate limiting: {'DISABILITATO' if not stats['rate_limiting_enabled'] else 'ABILITATO'}")
    print(f"📊 Cache size: {stats['cache_size']}/{stats['max_size']}")
    print()

    # Simula 1000 heartbeat consecutivi (molto più del vecchio limite di 100)
    print("🔄 Registrando 1000 heartbeat consecutivi...")
    start_time = time.time()

    for i in range(1000):
        await record_agent_heartbeat(
            brand_id="example-brand",
            llm_meta={
                "model_used": f"claude-3-5-haiku-20241022",
                "engine": "anthropic",
                "latency_ms": 1000 + (i % 500),
                "tokens_prompt": 100,
                "tokens_completion": 50,
            },
            context=f"agent_context_{i % 10}",  # 10 agenti diversi
            action=f"action_{i % 5}",         # 5 azioni diverse
            status="healthy",
        )

        if (i + 1) % 100 == 0:
            print(f"   ✓ Completati {i + 1}/1000 heartbeat")

    elapsed = time.time() - start_time
    print(f"✅ 1000 heartbeat completati in {elapsed:.2f} secondi")
    print(f"   Throughput: {1000/elapsed:.1f} heartbeat/secondo")
    print()

    # Verifica risultati
    print("📊 Risultati:")
    stats = get_cache_stats()
    print(f"   Cache size: {stats['cache_size']}/{stats['max_size']}")

    # Ottieni heartbeat per un agente specifico
    agent_heartbeat = get_cached_heartbeat("example-brand", "agent_context_0")
    if agent_heartbeat:
        print(f"   Agente 'agent_context_0' trovato in cache")
        print(f"   Status: {agent_heartbeat['status']}")
        print(f"   Model: {agent_heartbeat['llm_meta']['model_used']}")
        print(f"   Engine: {agent_heartbeat['llm_meta']['engine']}")

    # Ottieni tutti gli heartbeat per il brand
    all_heartbeats = get_all_cached_heartbeats("example-brand")
    print(f"   Totale agenti tracciati: {len(all_heartbeats)}")
    print()


async def example_rate_limiting_control():
    """Esempio di controllo del rate limiting."""

    print("🔧 Esempio: Controllo rate limiting")
    print("=" * 60)

    # Mostra stato corrente
    stats = get_cache_stats()
    current_status = "ABILITATO" if stats['rate_limiting_enabled'] else "DISABILITATO"
    print(f"📊 Stato corrente: {current_status}")
    print()

    # Se vuoi abilitare il rate limiting (opzionale)
    print("💡 Per abilitare il rate limiting se necessario:")
    print("   set_rate_limiting(True)")
    print()

    # Mostra come disabilitarlo (default)
    print("💡 Per disabilitare il rate limiting (default):")
    print("   set_rate_limiting(False)")
    print()

    # Esempio di abilitazione temporanea
    print("🔄 Abilitazione temporanea del rate limiting...")
    set_rate_limiting(True)

    stats = get_cache_stats()
    print(f"📊 Nuovo stato: {'ABILITATO' if stats['rate_limiting_enabled'] else 'DISABILITATO'}")
    print()

    # Disabilita nuovamente (default)
    print("🔄 Ripristino stato disabilitato (default)...")
    set_rate_limiting(False)

    stats = get_cache_stats()
    print(f"📊 Stato finale: {'ABILITATO' if stats['rate_limiting_enabled'] else 'DISABILITATO'}")
    print()


async def example_concurrent_heartbeats():
    """Esempio di heartbeat concorrenti senza limitazioni."""

    print("⚡ Esempio: Heartbeat concorrenti illimitati")
    print("=" * 60)

    # Crea 500 heartbeat concorrenti
    print("🔄 Registrando 500 heartbeat concorrenti...")
    start_time = time.time()

    tasks = [
        record_agent_heartbeat(
            brand_id="concurrent-brand",
            llm_meta={
                "model_used": "claude-3-5-sonnet-20241022",
                "engine": "anthropic",
                "latency_ms": 1500,
                "tokens_prompt": 200,
                "tokens_completion": 100,
            },
            context="concurrent_context",
            action="concurrent_action",
            status="healthy",
        )
        for _ in range(500)
    ]

    # Esegui tutti concorrentemente
    await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    print(f"✅ 500 heartbeat concorrenti completati in {elapsed:.2f} secondi")
    print(f"   Throughput concorrente: {500/elapsed:.1f} heartbeat/secondo")
    print()


async def main():
    """Esegui tutti gli esempi."""

    print("🎯 Sistema Heartbeat - Esempi di Utilizzo")
    print("=" * 60)
    print()

    await example_unlimited_heartbeats()
    await example_rate_limiting_control()
    await example_concurrent_heartbeats()

    print("🎉 Tutti gli esempi completati con successo!")
    print()
    print("📝 Note importanti:")
    print("   • Rate limiting è DISABILITATO di default")
    print("   • Puoi registrare heartbeat illimitati")
    print("   • Cache è limitata a 1000 entries (LRU)")
    print("   • Heartbeat failures non impattano la pipeline principale")
    print()


if __name__ == "__main__":
    asyncio.run(main())
