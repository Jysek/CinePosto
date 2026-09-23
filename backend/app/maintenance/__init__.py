"""Script di manutenzione del database (non fanno parte del servizio).

Eseguibili solo da riga di comando, mai chiamati dai router: sono operazioni
lente o distruttive che richiedono la lettura esplicita di un piano (dry-run)
prima di scrivere qualsiasi cosa.
"""
