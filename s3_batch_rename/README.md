````markdown
# S3 Multi-Replace Rename

Script Python per rinominare in blocco chiavi S3 sostituendo una sottostringa (`old_segment`) con un’altra (`new_segment`) **ovunque nel path**, non solo all’inizio.  
Esegue `COPY` → `DELETE`, perché S3 non supporta `rename` diretto.

---

## Funzionalità

- Cerca tutti gli oggetti che contengono `old_segment` nel nome.
- Crea una nuova chiave sostituendo `old_segment` con `new_segment`.
- Copia ogni oggetto nella nuova posizione.
- Cancella la vecchia chiave dopo la copia.
- Supporta modalità **dry-run** per simulare le operazioni.
- Supporta **multithreading** per migliorare la velocità.
- Gestisce collisioni tra chiavi generate.

---

## Requisiti

- Python ≥ 3.8  
- [boto3](https://pypi.org/project/boto3/)

Installa con:

```bash
pip install boto3
````

È necessario configurare le credenziali AWS (tramite `aws configure`, variabili d’ambiente o IAM role).

---

## Permessi richiesti (IAM)

L’utente o ruolo che esegue lo script deve avere:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:ListBucket",
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject"
  ],
  "Resource": [
    "arn:aws:s3:::<bucket-name>",
    "arn:aws:s3:::<bucket-name>/*"
  ]
}
```

---

## Uso

Esegui:

```bash
python rename_segment.py
```

Esempio nel file:

```python
rename_segment(
    bucket="nome-del-tuo-bucket",
    old_segment="/old/",
    new_segment="/new/",
    search_prefix="pippo/",   # opzionale, migliora performance
    dry_run=True,             # True = simula, False = esegue
    max_workers=16,           # thread per parallelizzare
    allow_collisions=False,   # True = sovrascrive chiavi duplicate
)
```

---

## Parametri principali

| Parametro          | Tipo          | Descrizione                                                       |
| ------------------ | ------------- | ----------------------------------------------------------------- |
| `bucket`           | `str`         | Nome del bucket S3.                                               |
| `old_segment`      | `str`         | Sottostringa da sostituire (es. `/old/`).                         |
| `new_segment`      | `str`         | Nuova sottostringa (es. `/new/`).                                 |
| `search_prefix`    | `str \| None` | Prefisso iniziale per limitare la ricerca.                        |
| `dry_run`          | `bool`        | Se `True`, mostra solo le operazioni senza eseguirle.             |
| `max_workers`      | `int`         | Numero di thread paralleli.                                       |
| `allow_collisions` | `bool`        | Se `False`, salta chiavi che genererebbero lo stesso nome finale. |

---

## Output

Durante l’esecuzione:

* In modalità `dry_run=True`:

  ```
  [DRY RUN] COPY pippo/old/x.txt -> pippo/new/x.txt
  [DRY RUN] DELETE pippo/old/x.txt
  ```
* In modalità esecuzione reale:

  ```
  Oggetti spostati: 324
  Byte copiati: 1.2e+09
  Saltate collisioni: 3 destinazioni
  ```

---

## Note operative

* **Atomicità:** non transazionale. Se interrotto, puoi rilanciarlo: gli oggetti già copiati vengono sovrascritti.
* **Versioned bucket:** `delete_object` crea un delete marker, non elimina le vecchie versioni.
* **Prestazioni:** usa `max_workers` per scalare su grandi bucket.
* **Collisioni:** se più chiavi diventano uguali dopo la sostituzione, vengono saltate a meno di `allow_collisions=True`.

---

## Licenza

MIT License

```
```
