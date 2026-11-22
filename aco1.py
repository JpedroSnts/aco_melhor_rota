import math
import random
from datetime import datetime


def buscar_rota_aco(
    grafo,
    origem,
    destino,
    formigas,
    iteracoes,
    alfa=0.3,
    beta=0.5,
    evaporacao=0.5,
    q=None,
    seed=None,
    atributo="length",
    tau_max=1.0,
    tau_min_fator=0.01,
    n_depositantes=1,
    restricoes_conversao=None,
):
    """Busca uma rota com ACO e retorna (rota, custo)."""
    if origem not in grafo or destino not in grafo:
        raise ValueError("Origem ou destino nao encontrado no grafo.")
    if not grafo.is_directed():
        raise ValueError(
            "O ACO precisa de um grafo dirigido. Carregue a rede com network_type='drive'."
        )
    if iteracoes <= 0 or formigas <= 0:
        raise ValueError("O numero de formigas e iteracoes precisa ser maior que zero.")

    if origem == destino:
        return [origem], 0.0

    # Calcula cada custo uma vez; caminhos usam o menor custo entre arestas paralelas.
    custos = {}
    for u, v in grafo.edges():
        dados = grafo.get_edge_data(u, v)
        if grafo.is_multigraph():
            dados = dados.values()
        else:
            dados = [dados]
        custos[u, v] = min(float(aresta.get(atributo, 1.0)) for aresta in dados)

    adjacencias = {no: list(grafo.successors(no)) for no in grafo}
    restricoes_conversao = set(restricoes_conversao or ())

    sorteio = random.Random(seed)
    feromonios = {aresta: tau_max for aresta in custos}
    melhor_rota = None
    melhor_custo = float("inf")
    iteracao_melhor = 0
    historico_melhorias = []
    q_efetivo = q
    intervalo_log = max(1, iteracoes // 20)
    tau_min = tau_max * tau_min_fator

    for numero_iteracao in range(1, iteracoes + 1):
        rotas = []
        for _ in range(formigas):
            rota = [origem]
            visitados = {origem}
            custo_rota = 0.0

            while rota[-1] != destino and len(rota) < len(grafo):
                atual = rota[-1]
                opcoes = []

                for proxima in adjacencias[atual]:
                    if proxima in visitados:
                        continue
                    if len(rota) > 1 and (rota[-2], atual, proxima) in restricoes_conversao:
                        continue

                    custo = custos[atual, proxima]
                    if not math.isfinite(custo) or custo < 0:
                        continue

                    peso = max(feromonios[atual, proxima], 1e-12) ** alfa
                    peso *= (1 / max(custo, 0.001)) ** beta
                    if not math.isfinite(peso) or peso <= 0:
                        peso = 1e-300
                    opcoes.append((proxima, peso, custo))

                if not opcoes:
                    break

                proxima, _, custo = sorteio.choices(
                    opcoes, weights=[opcao[1] for opcao in opcoes], k=1
                )[0]
                rota.append(proxima)
                visitados.add(proxima)
                custo_rota += custo

            if rota[-1] == destino:
                rotas.append((rota, custo_rota))
                if custo_rota < melhor_custo:
                    melhor_rota = rota
                    melhor_custo = custo_rota
                    iteracao_melhor = numero_iteracao
                    historico_melhorias.append((numero_iteracao, custo_rota))

        if q_efetivo is None and rotas:
            q_efetivo = min(custo for _, custo in rotas)

        for aresta in feromonios:
            feromonios[aresta] *= 1 - evaporacao

        for rota, custo in sorted(rotas, key=lambda item: item[1])[:n_depositantes]:
            deposito = q_efetivo / max(custo, 0.001)
            for aresta in zip(rota, rota[1:]):
                feromonios[aresta] += deposito

        for aresta, valor in feromonios.items():
            feromonios[aresta] = min(max(valor, tau_min), tau_max)

        if numero_iteracao == 1 or numero_iteracao % intervalo_log == 0 or numero_iteracao == iteracoes:
            if melhor_rota is None:
                melhor = "ainda nao encontrada"
                convergencia = "sem rota ainda"
            else:
                melhor = f"{melhor_custo:.0f}"
                convergencia = (
                    f"melhor desde a iteracao {iteracao_melhor} "
                    f"({numero_iteracao - iteracao_melhor} sem melhora)"
                )
            percentual = numero_iteracao * 100 // iteracoes
            print(
                f"ACO: iteracao {numero_iteracao}/{iteracoes} ({percentual}%) | "
                f"rotas validas nesta iteracao: {len(rotas)} | "
                f"melhor custo ({atributo}): {melhor} | {convergencia} | "
                f"{datetime.now()}",
                flush=True,
            )

    if melhor_rota is None:
        raise ValueError("O ACO nao encontrou uma rota. Aumente o numero de formigas ou iteracoes.")

    sem_melhora = iteracoes - iteracao_melhor
    print(
        f"ACO: convergiu na iteracao {iteracao_melhor}/{iteracoes} "
        f"({iteracao_melhor * 100 // iteracoes}% do total) | "
        f"{sem_melhora} iteracoes finais sem melhora | "
        f"{len(historico_melhorias)} melhoras no total | "
        f"ultimas melhoras (iteracao, custo): {historico_melhorias[-5:]}",
        flush=True,
    )

    return melhor_rota, melhor_custo
