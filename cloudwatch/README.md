# cloudwatch-tail

Uno script Python per “tailing” dei log CloudWatch di un cluster EKS, filtrando gli stream e recuperando gli eventi più recenti.

---

## Requisiti

- Python 3.7+
- [boto3](https://pypi.org/project/boto3/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

---

## Installazione

1. Clona o copia questo repository nella tua macchina.
2. Crea file .env
```bash
AWS_ACCESS_KEY_ID=TUO_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=TUO_SECRET_KEY
AWS_DEFAULT_REGION=eu-west-1
```
3. Avvia
```bash
    ./podman_run.sh
```
4. Uso
```bash
python tail_cloudwatch.py --filter api-server --since 1h
```

- python tail_cloudwatch.py 
- [--filter <substring>] Sottostringa da cercare nel nome del log stream (default: utility).
- [--since <durata>] Periodo da cui partire per il “tail” dei log, con formato:
    - 30m → ultimi 30 minuti
    - 1h → ultima 1 ora
    - (default: 5m)
```