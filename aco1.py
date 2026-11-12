import random  # gerador de numeros aleatorios (roleta e seed)
import math  # funcoes matematicas (isfinite, sin, cos, asin, sqrt, radians)
from datetime import datetime  # data/hora nos logs de progresso


def buscar_rota_aco(grafo, origem, destino, formigas, iteracoes,
                    alfa=0.3, beta=0.5, evaporacao=0.5, q=None, seed=None,
                    atributo="length", gama=0.0,
                    tau_max=1.0, tau_min_fator=0.01, n_depositantes=1,
                    estagnacao=None, comparar_dijkstra=False):
    """Retorna (rota, custo) otimizando o atributo de aresta informado.

    atributo:          atributo da aresta usado como custo e heuristica local
                       (ex.: "length", "travel_time" ou um atributo proprio).
    gama:              peso da heuristica de direcao ao destino (0 desliga).
                       Exige nos com "x" (longitude) e "y" (latitude).
    tau_max:           teto do feromonio (tambem o valor inicial e o de reinicio).
    tau_min_fator:     piso do feromonio = tau_max * tau_min_fator. Mantem toda
                       aresta com chance de ser escolhida (estilo MAX-MIN AS).
    n_depositantes:    quantas das melhores rotas da iteracao depositam feromonio.
    q:                 constante de deposito. None = automatico: usa o custo da
                       primeira rota valida, deixando o deposito na casa de 1.
    estagnacao:        se informado, reinicia os feromonios apos N iteracoes sem
                       melhora do melhor global (a melhor rota e mantida).
    comparar_dijkstra: se True, compara o resultado com o caminho otimo exato.
    """
    if origem not in grafo or destino not in grafo:  # confere se os dois nos existem
        raise ValueError("Origem ou destino nao encontrado no grafo.")  # erro claro

    def custo_aresta(u, v):  # custo da aresta u->v
        arestas = grafo.get_edge_data(u, v).values()  # arestas paralelas (MultiDiGraph)
        return min(float(a.get(atributo, 1.0)) for a in arestas)  # menor custo; 1.0 se faltar o atributo

    def distancia(rota):  # custo total de uma rota
        return sum(custo_aresta(u, v) for u, v in zip(rota, rota[1:]))  # soma dos custos dos pares consecutivos

    # Distancia em linha reta (haversine, em metros) de cada no ate o destino.
    cache_dist_destino = {}  # evita recalcular a mesma distancia
    if gama > 0:  # so prepara se a heuristica de direcao estiver ligada
        if "x" not in grafo.nodes[destino] or "y" not in grafo.nodes[destino]:  # exige coordenadas
            raise ValueError(
                "gama > 0 exige nos com atributos 'x' e 'y' (coordenadas)."
            )  # erro explicando o requisito
        lon_d = math.radians(grafo.nodes[destino]["x"])  # longitude do destino em radianos
        lat_d = math.radians(grafo.nodes[destino]["y"])  # latitude do destino em radianos

        def dist_destino(no):  # distancia em metros do no ate o destino
            if no not in cache_dist_destino:  # calcula so se nao estiver no cache
                lon = math.radians(grafo.nodes[no]["x"])  # longitude do no
                lat = math.radians(grafo.nodes[no]["y"])  # latitude do no
                h = (math.sin((lat_d - lat) / 2) ** 2  # termo da latitude (haversine)
                     + math.cos(lat) * math.cos(lat_d)  # correcao da curvatura
                     * math.sin((lon_d - lon) / 2) ** 2)  # termo da longitude
                cache_dist_destino[no] = 2 * 6371000.0 * math.asin(math.sqrt(h))  # 2*R*asin(sqrt(h)), R em metros
            return cache_dist_destino[no]  # valor calculado ou do cache

    if origem == destino:  # caso trivial
        return [origem], 0.0  # rota de um no, custo zero

    tau_min = tau_max * tau_min_fator  # piso do feromonio
    sorteio = random.Random(seed)  # gerador proprio, com seed opcional
    feromonios = {(u, v): tau_max for u, v in grafo.edges()}  # comeca todas as arestas no teto
    melhor_rota = None  # melhor rota global
    melhor_distancia = float("inf")  # custo da melhor rota global
    iteracao_melhor = 0  # iteracao em que o recorde atual surgiu
    historico_melhorias = []  # lista de (iteracao, custo) a cada melhora
    iteracao_reinicio = 0  # iteracao do ultimo reinicio de feromonios
    reinicios = 0  # quantos reinicios ocorreram
    q_efetivo = q  # q usado de fato (se None, definido na 1a rota valida)

    intervalo_log = max(1, iteracoes // 20)  # log a cada 5%
    for numero_iteracao in range(1, iteracoes + 1):  # laco principal
        rotas = []  # rotas validas desta iteracao
        for _ in range(formigas):  # cada formiga constroi uma rota
            rota = [origem]  # parte da origem
            visitadas = {origem}  # nos visitados (evita ciclos)

            while rota[-1] != destino and len(rota) < len(grafo):  # anda ate o destino ou esgotar nos
                atual = rota[-1]  # no atual
                opcoes = []  # candidatos (no, peso)
                for proxima in grafo.successors(atual):  # vizinhos alcancaveis
                    if proxima in visitadas:  # nao revisita nos
                        continue
                    comprimento = custo_aresta(atual, proxima)  # custo ate o vizinho
                    if not math.isfinite(comprimento) or comprimento < 0:  # ignora custo invalido
                        continue
                    feromonio = max(feromonios[(atual, proxima)], 1e-12)  # feromonio com piso de seguranca
                    peso = feromonio ** alfa  # tau^alfa
                    peso *= (1.0 / max(comprimento, 0.001)) ** beta  # (1/custo)^beta
                    if gama > 0:  # heuristica opcional de direcao
                        peso *= (1.0 / max(dist_destino(proxima), 1.0)) ** gama  # (1/dist ao destino)^gama
                    if not math.isfinite(peso) or peso <= 0:  # peso invalido ou underflow
                        peso = 1e-300  # minimo positivo para a roleta
                    opcoes.append((proxima, peso))  # registra o candidato

                if not opcoes:  # beco sem saida
                    break  # formiga desiste

                proxima, _ = sorteio.choices(
                    opcoes, weights=[peso for _, peso in opcoes], k=1
                )[0]  # roleta: sorteia proporcional ao peso
                rota.append(proxima)  # avanca para o no sorteado
                visitadas.add(proxima)  # marca como visitado

            if rota[-1] == destino:  # so rotas que chegaram contam
                custo = distancia(rota)  # custo total
                rotas.append((rota, custo))  # guarda para o deposito
                if custo < melhor_distancia:  # novo recorde global?
                    melhor_rota, melhor_distancia = rota, custo  # atualiza o recorde
                    iteracao_melhor = numero_iteracao  # guarda a iteracao da melhora
                    historico_melhorias.append((numero_iteracao, custo))  # registra no historico

        if q_efetivo is None and rotas:  # q automatico ainda nao definido e ha rota valida
            q_efetivo = min(custo for _, custo in rotas)  # usa o custo da melhor rota: deposito ~1 por aresta

        for aresta in feromonios:  # evaporacao em todas as arestas
            feromonios[aresta] *= (1.0 - evaporacao)  # perde a fracao evaporada

        for rota, custo in sorted(rotas, key=lambda rc: rc[1])[:n_depositantes]:  # so as N melhores rotas depositam
            deposito = q_efetivo / max(custo, 0.001)  # mais barata = mais feromonio
            for u, v in zip(rota, rota[1:]):  # cada aresta da rota
                feromonios[(u, v)] += deposito  # reforca a aresta

        for aresta in feromonios:  # aplica limites MAX-MIN
            feromonios[aresta] = min(max(feromonios[aresta], tau_min), tau_max)  # mantem entre tau_min e tau_max

        ultima_referencia = max(iteracao_melhor, iteracao_reinicio)  # ultimo marco: melhora ou reinicio
        if estagnacao and numero_iteracao - ultima_referencia >= estagnacao:  # estagnou por N iteracoes
            for aresta in feromonios:  # reinicia todos os feromonios
                feromonios[aresta] = tau_max  # volta ao valor inicial (exploracao total)
            iteracao_reinicio = numero_iteracao  # marca quando reiniciou
            reinicios += 1  # conta o reinicio

        if (
            numero_iteracao == 1  # sempre loga a primeira
            or numero_iteracao % intervalo_log == 0  # e a cada 5%
            or numero_iteracao == iteracoes  # e a ultima
        ):
            percentual = numero_iteracao * 100 // iteracoes  # progresso em %
            if melhor_rota is not None:  # ja existe rota valida
                convergencia = (
                    f"melhor desde a iteracao {iteracao_melhor} "  # quando o recorde surgiu
                    f"({numero_iteracao - iteracao_melhor} sem melhora)"  # ha quanto tempo nao melhora
                )
                melhor = f"{melhor_distancia:.0f}"  # custo sem casas decimais
            else:
                convergencia = "sem rota ainda"  # nada encontrado
                melhor = "ainda nao encontrada"  # idem
            print(
                f"ACO: iteracao {numero_iteracao}/{iteracoes} ({percentual}%) | "  # progresso
                f"rotas validas nesta iteracao: {len(rotas)} | "  # formigas que chegaram
                f"melhor custo ({atributo}): {melhor} | {convergencia} | "  # custo e convergencia
                f"reinicios: {reinicios} | {datetime.now()}",  # reinicios e horario
                flush=True,  # saida imediata
            )

    if melhor_rota is None:  # nenhuma rota em todas as iteracoes
        raise ValueError(
            "O ACO nao encontrou uma rota. Aumente o numero de formigas ou iteracoes."
        )  # erro com sugestao

    iteracoes_sem_melhora = iteracoes - iteracao_melhor  # iteracoes finais sem melhora
    print(  # resumo final de convergencia
        f"ACO: convergiu na iteracao {iteracao_melhor}/{iteracoes} "  # iteracao da melhor solucao
        f"({iteracao_melhor * 100 // iteracoes}% do total) | "  # em percentual
        f"{iteracoes_sem_melhora} iteracoes finais sem melhora | "  # estagnacao final
        f"{len(historico_melhorias)} melhoras no total | "  # quantas vezes o recorde caiu
        f"{reinicios} reinicios | "  # reinicios por estagnacao
        f"ultimas melhoras (iteracao, custo): {historico_melhorias[-5:]}",  # ultimas 5 melhoras
        flush=True,
    )

    if comparar_dijkstra:  # validacao opcional contra o otimo exato
        import networkx as nx  # importa so se for usar
        try:
            otimo = nx.shortest_path_length(grafo, origem, destino, weight=atributo)  # custo otimo exato
            gap = (melhor_distancia / otimo - 1) * 100 if otimo > 0 else 0.0  # distancia percentual do otimo
            print(
                f"Dijkstra: otimo = {otimo:.2f} | ACO = {melhor_distancia:.2f} | gap = {gap:.2f}%",
                flush=True,
            )  # mostra a comparacao
        except nx.NetworkXNoPath:  # nao ha caminho no grafo
            print("Dijkstra: nao existe caminho entre origem e destino.", flush=True)  # avisa

    return melhor_rota, melhor_distancia  # melhor rota global e seu custo