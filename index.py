import osmnx as ox
import matplotlib.pyplot as plt

place_name = [
    "Gonzaga, Santos, São Paulo, Brazil",
    "Encruzilhada, Santos, São Paulo, Brazil",
    "Macuco, Santos, São Paulo, Brazil",
    "Boqueirão, Santos, São Paulo, Brazil"]
G = ox.graph_from_place(place_name, network_type="drive")

nodes, edges = ox.graph_to_gdfs(G)

print(edges)

ox.plot_graph(G, node_size=0, edge_color="yellow", edge_linewidth=0.2, bgcolor="black")
