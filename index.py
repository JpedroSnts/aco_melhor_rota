import osmnx as ox
import matplotlib.pyplot as plt

from aco1 import buscar_rota_aco
from restricoes import buscar_restricoes_conversao


BAIRROS = [
  "Santos, Sao Paulo, Brazil"
]

# Coordenadas em formato (latitude, longitude).

ROTAS_TESTE = [
    {
        "origem": (-23.963679, -46.321569), 
        "destino": (-23.959459, -46.324828),
        "formigas": 4043,
        "iteracoes": 10
    },
    {
        "origem": (-23.961570, -46.335135), 
        "destino": (-23.985052, -46.298377),
        "formigas": 4043,
        "iteracoes": 7550
    },
    {
        "origem": (-23.988425, -46.296914), 
        "destino": (-23.932791, -46.331549),
        "formigas": 4043,
        "iteracoes": 25
    }
]

IDX_ROTA = 1
ORIGEM = ROTAS_TESTE[IDX_ROTA]["origem"]
DESTINO = ROTAS_TESTE[IDX_ROTA]["destino"]

def executar_rota(origem=ORIGEM, destino=DESTINO):
    grafo = ox.graph_from_place(BAIRROS, network_type="drive")
    restricoes = buscar_restricoes_conversao(grafo)
    print(f"Restricoes de conversao carregadas: {len(restricoes)}")
    no_origem = ox.distance.nearest_nodes(grafo, X=origem[1], Y=origem[0])
    no_destino = ox.distance.nearest_nodes(grafo, X=destino[1], Y=destino[0])

    #quantidade_nos = grafo.number_of_nodes()
    formigas = ROTAS_TESTE[IDX_ROTA]["formigas"]
    iteracoes = ROTAS_TESTE[IDX_ROTA]["iteracoes"]

    rota, metros = buscar_rota_aco(
        grafo,
        no_origem,
        no_destino,
        formigas,
        iteracoes,
        seed=42,
        restricoes_conversao=restricoes,
    )
    print(f"Distancia da rota: {metros:.0f} m")

    _, ax = ox.plot_graph(
        grafo, node_size=0, edge_color="gray", show=False, close=False
    )
    ox.plot_graph_route(
        grafo, rota, ax=ax, route_color="red", route_linewidth=4,
        node_size=0, show=False, close=False,
    )
    plt.show()
    return rota, metros


if __name__ == "__main__":
    executar_rota()
