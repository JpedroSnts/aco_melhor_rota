import random
import math
from datetime import datetime

def buscar_rota_aco(grafo, origem, destino, formigas=1000, iteracoes=20000,
                    alfa=0.5, beta=0.5, evaporacao=0.5, q=1.0, seed=None):
    """Retorna (rota, distancia) usando o comprimento das ruas em metros."""
    if origem not in grafo or destino not in grafo:
        raise ValueError("Origem ou destino nao encontrado no grafo.")

    def distancia(rota):
        total = 0.0
        for u, v in zip(rota, rota[1:]):
            arestas = grafo.get_edge_data(u, v).values()
            total += min(float(a.get("length", 1.0)) for a in arestas)
        return total

    if origem == destino:
        return [origem], 0.0

    sorteio = random.Random(seed)
    feromonios = {(u, v): 1.0 for u, v in grafo.edges()}
    melhor_rota = None
    melhor_distancia = float("inf")

    intervalo_log = max(1, iteracoes // 20)
    for numero_iteracao in range(1, iteracoes + 1):
        rotas = []
        for _ in range(formigas):
            rota = [origem]
            visitadas = {origem}

            while rota[-1] != destino and len(rota) < len(grafo):
                atual = rota[-1]
                opcoes = []
                for proxima in grafo.successors(atual):
                    if proxima in visitadas:
                        continue
                    arestas = grafo.get_edge_data(atual, proxima).values()
                    comprimento = min(float(a.get("length", 1.0)) for a in arestas)
                    if not math.isfinite(comprimento) or comprimento < 0:
                        continue
                    feromonio = max(feromonios[(atual, proxima)], 1e-12)
                    peso = feromonio ** alfa
                    peso *= (1.0 / max(comprimento, 0.001)) ** beta
                    # Mantem a roleta utilizavel mesmo com pesos muito pequenos.
                    if not math.isfinite(peso) or peso <= 0:
                        peso = 1e-300
                    opcoes.append((proxima, peso))

                if not opcoes:
                    break

                proxima, _ = sorteio.choices(
                    opcoes, weights=[peso for _, peso in opcoes], k=1
                )[0]
                rota.append(proxima)
                visitadas.add(proxima)

            if rota[-1] == destino:
                custo = distancia(rota)
                rotas.append((rota, custo))
                if custo < melhor_distancia:
                    melhor_rota, melhor_distancia = rota, custo

        for aresta in feromonios:
            feromonios[aresta] = max(
                feromonios[aresta] * (1.0 - evaporacao), 1e-12
            )
        for rota, custo in rotas:
            deposito = q / max(custo, 0.001)
            for u, v in zip(rota, rota[1:]):
                feromonios[(u, v)] += deposito

        if (
            numero_iteracao == 1
            or numero_iteracao % intervalo_log == 0
            or numero_iteracao == iteracoes
        ):
            percentual = numero_iteracao * 100 // iteracoes
            melhor = (
                f"{melhor_distancia:.0f} m"
                if melhor_rota is not None
                else "ainda nao encontrada"
            )
            print(
                f"ACO: iteracao {numero_iteracao}/{iteracoes} ({percentual}%) | "
                f"rotas validas nesta iteracao: {len(rotas)} | melhor distancia: {melhor} | {datetime.now()}",
                flush=True,
            )

    if melhor_rota is None:
        raise ValueError(
            "O ACO nao encontrou uma rota. Aumente o numero de formigas ou iteracoes."
        )
    return melhor_rota, melhor_distancia
