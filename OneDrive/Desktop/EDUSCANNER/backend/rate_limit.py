"""
Rate limiting simples, em memória, para rotas sensíveis (Seção 24):
login (evitar força bruta de senha) e o scanner (evitar abuso do
endpoint mais caro em CPU do sistema).

Implementação deliberadamente simples (sem Redis) porque o EDUSCANNER
roda como processo único por padrão. Se o deploy migrar para múltiplos
workers/instâncias, troque este armazenamento em memória por um
backend compartilhado (Redis, por exemplo) — a interface abaixo
(`check`) já isola essa decisão em um único lugar.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self.window_seconds
            while hits and hits[0] < cutoff:
                hits.pop(0)
            if len(hits) >= self.max_attempts:
                retry_after = int(self.window_seconds - (now - hits[0]))
                raise HTTPException(
                    status_code=429,
                    detail="Muitas tentativas em pouco tempo. Aguarde um instante e tente novamente.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )
            hits.append(now)


def _client_key(request: Request) -> str:
    # request.client pode ser None atrás de alguns proxies de teste;
    # nesse caso, cai para um bucket único (ainda protege contra abuso
    # básico de um único processo cliente).
    return request.client.host if request.client else "unknown"


# Login: no máximo 8 tentativas por minuto por IP — o bastante para um
# professor digitar a senha errada algumas vezes, pouco o bastante para
# dificultar força bruta.
login_limiter = RateLimiter(max_attempts=8, window_seconds=60)

# Scanner: é a rota mais cara em CPU (visão computacional); limitamos
# para evitar que um único cliente sature o servidor.
scanner_limiter = RateLimiter(max_attempts=30, window_seconds=60)


def enforce_login_rate_limit(request: Request) -> None:
    login_limiter.check(_client_key(request))


def enforce_scanner_rate_limit(request: Request) -> None:
    scanner_limiter.check(_client_key(request))
