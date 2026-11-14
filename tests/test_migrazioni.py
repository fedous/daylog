from alembic import command


def test_i_modelli_e_le_migrazioni_sono_allineati(config_vuoto):
    command.upgrade(config_vuoto, "head")

    # Fallisce se i modelli hanno qualcosa che le migrazioni non creano
    command.check(config_vuoto)


def test_le_migrazioni_vanno_avanti_e_indietro(config_vuoto):
    command.upgrade(config_vuoto, "head")
    command.downgrade(config_vuoto, "base")
    # Se il downgrade ha lasciato qualcosa (es. una tabella), il secondo upgrade fallisce
    command.upgrade(config_vuoto, "head")
