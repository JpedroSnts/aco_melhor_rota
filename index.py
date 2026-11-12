import osmnx as ox
import matplotlib.pyplot as plt

from aco1 import buscar_rota_aco


BAIRROS = [
    "Gonzaga, Santos, Sao Paulo, Brazil",
    "Encruzilhada, Santos, Sao Paulo, Brazil",
    "Campo Grande, Santos, Sao Paulo, Brazil",
    "Boqueirão, Santos, Sao Paulo, Brazil"
]

# Coordenadas em formato (latitude, longitude).
ORIGEM = (-23.957341, -46.341312)
DESTINO = (-23.970372, -46.322068)


def executar_rota(origem=ORIGEM, destino=DESTINO):
    grafo = ox.graph_from_place(BAIRROS, network_type="drive")
    no_origem = ox.distance.nearest_nodes(grafo, X=origem[1], Y=origem[0])
    no_destino = ox.distance.nearest_nodes(grafo, X=destino[1], Y=destino[0])

    quantidade_nos = grafo.number_of_nodes()
    formigas = quantidade_nos
    iteracoes = quantidade_nos * 6

    rota, metros = buscar_rota_aco(grafo, no_origem, no_destino, formigas, iteracoes, seed=42)
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
