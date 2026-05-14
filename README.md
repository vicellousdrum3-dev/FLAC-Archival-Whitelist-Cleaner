# FLAC Archival Whitelist Cleaner — Railway Edition

Web app minimale per pubblicare su Railway la procedura `flac_archival_whitelist_recursive.sh`.

## Cosa fa

1. Riceve in upload uno ZIP con una o più cartelle contenenti file `.flac` / `.FLAC`.
2. Estrae lo ZIP in una cartella temporanea.
3. Esegue lo script ricorsivo di pulizia metadati FLAC.
4. Crea in ogni cartella contenente FLAC:
   - `report_flac_archival_whitelist.tsv`
   - `verifica_pulizia_whitelist.txt`
5. Ricomprime tutto e restituisce lo ZIP finale.

## File del progetto

```text
flac-cleaner-railway/
├── Dockerfile
├── requirements.txt
├── app.py
├── flac_archival_whitelist_recursive.sh
├── README.md
└── .gitignore
```

## Deploy su Railway

1. Crea un nuovo repository GitHub.
2. Carica tutti i file di questa cartella nella root del repository.
3. In Railway crea un nuovo progetto.
4. Scegli **GitHub Repository**.
5. Seleziona il repository.
6. Railway userà il `Dockerfile` per costruire il servizio.
7. Aggiungi un Volume con mount path:

```text
/data
```

8. Genera il dominio pubblico del servizio.
9. Apri il dominio e carica uno ZIP con i FLAC.

## Variabili opzionali

Puoi aggiungere queste variabili in Railway:

```text
PROCESS_TIMEOUT_SECONDS=7200
DATA_DIR=/data
```

Se configuri un Volume Railway, l'app usa automaticamente `RAILWAY_VOLUME_MOUNT_PATH` quando disponibile.

## Test locale con Docker

```sh
docker build -t flac-cleaner-railway .
docker run --rm -p 8080:8080 -v "$PWD/data:/data" flac-cleaner-railway
```

Poi apri:

```text
http://localhost:8080
```

## Nota importante

La procedura modifica i FLAC estratti dallo ZIP, non i file originali presenti sul tuo computer. Il risultato viene scaricato come nuovo ZIP.


## License

This project is licensed under the MIT License. See the LICENSE file for details.
