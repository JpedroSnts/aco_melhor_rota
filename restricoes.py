"""Leitura de restricoes de conversao do OpenStreetMap (Overpass)."""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _ids_osm(valor):
    """Normaliza o atributo osmid, que pode ser inteiro ou lista de inteiros."""
    if isinstance(valor, (list, tuple, set)):
        return {str(item) for item in valor}
    return {str(valor)}


def buscar_restricoes_conversao(grafo):
    """Retorna conversoes proibidas como triplas (no_anterior, via, proximo).

    Busca relacoes OSM `type=restriction` dentro dos limites do grafo. Sao
    consideradas restricoes permanentes com via em um unico no. Restricoes
    condicionais e relacoes com via em uma rua inteira sao ignoradas.
    """
    latitudes = [float(dados["y"]) for _, dados in grafo.nodes(data=True)]
    longitudes = [float(dados["x"]) for _, dados in grafo.nodes(data=True)]
    sul, norte = min(latitudes), max(latitudes)
    oeste, leste = min(longitudes), max(longitudes)

    consulta = (
        "[out:json][timeout:90];"
        f'relation["type"="restriction"]({sul},{oeste},{norte},{leste});'
        "out body;"
    )
    requisicao = Request(
        OVERPASS_URL,
        data=urlencode({"data": consulta}).encode("utf-8"),
        headers={"User-Agent": "otimizacao-rota-aco/1.0"},
    )
    try:
        with urlopen(requisicao, timeout=120) as resposta:
            dados_osm = json.loads(resposta.read().decode("utf-8"))
    except Exception as erro:
        raise RuntimeError(
            "Nao foi possivel carregar as restricoes de conversao do OpenStreetMap. "
            "A busca foi interrompida para nao ignorar conversoes proibidas."
        ) from erro

    # Mapeia os OSM way IDs para nos de entrada e saida no grafo dirigido.
    entradas = {}
    saidas = {}
    nos_por_osmid = {str(no): no for no in grafo.nodes}
    if grafo.is_multigraph():
        arestas = grafo.edges(keys=True, data=True)
        for u, v, _, atributos in arestas:
            for osmid in _ids_osm(atributos.get("osmid", [])):
                entradas.setdefault((osmid, str(v)), set()).add(u)
                saidas.setdefault((osmid, str(u)), set()).add(v)
    else:
        for u, v, atributos in grafo.edges(data=True):
            for osmid in _ids_osm(atributos.get("osmid", [])):
                entradas.setdefault((osmid, str(v)), set()).add(u)
                saidas.setdefault((osmid, str(u)), set()).add(v)

    proibidas = set()
    ignoradas = 0
    nao_mapeadas = 0
    for relacao in dados_osm.get("elements", []):
        tags = relacao.get("tags", {})
        regra = (
            tags.get("restriction:motorcar")
            or tags.get("restriction:motor_vehicle")
            or tags.get("restriction:vehicle")
            or tags.get("restriction")
        )
        if not regra:
            continue
        excecoes = set(tags.get("except", "").replace(" ", "").split(";"))
        if excecoes.intersection({"motorcar", "motor_vehicle", "vehicle"}):
            continue
        if "restriction:conditional" in tags:
            ignoradas += 1
            continue

        membros = relacao.get("members", [])
        de = [m["ref"] for m in membros if m.get("role") == "from" and m.get("type") == "way"]
        para = [m["ref"] for m in membros if m.get("role") == "to" and m.get("type") == "way"]
        via = [m["ref"] for m in membros if m.get("role") == "via" and m.get("type") == "node"]
        vias_rua = [m for m in membros if m.get("role") == "via" and m.get("type") != "node"]
        if len(de) != 1 or len(para) != 1 or len(via) != 1 or vias_rua:
            ignoradas += 1
            continue

        no_via = str(via[0])
        no_via_grafo = nos_por_osmid.get(no_via)
        if no_via_grafo is None:
            nao_mapeadas += 1
            continue
        nos_entrada = entradas.get((str(de[0]), no_via), set())
        nos_saida = saidas.get((str(para[0]), no_via), set())
        if not nos_entrada or not nos_saida:
            # Via fora do recorte, ou way relation nao mapeada neste grafo.
            nao_mapeadas += 1
            continue

        if regra.startswith("only_"):
            todos_destinos = set(grafo.successors(no_via_grafo))
            for anterior in nos_entrada:
                for proximo in todos_destinos - nos_saida:
                    proibidas.add((anterior, no_via_grafo, proximo))
        elif regra.startswith("no_"):
            for anterior in nos_entrada:
                for proximo in nos_saida:
                    proibidas.add((anterior, no_via_grafo, proximo))

    if ignoradas:
        print(f"Aviso: {ignoradas} restricoes OSM condicionais ou complexas nao foram aplicadas.")
    if nao_mapeadas:
        print(f"Aviso: {nao_mapeadas} restricoes OSM nao corresponderam as arestas carregadas.")
    return proibidas
