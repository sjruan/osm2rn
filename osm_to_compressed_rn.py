import networkx as nx
import osmium as o
import argparse
from osm_to_rn import store_shp
import copy


class OSM2RNHandler(o.SimpleHandler):

    def __init__(self, rn):
        super(OSM2RNHandler, self).__init__()
        self.candi_highway_types = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
                                    'residential', 'motorway_link', 'trunk_link', 'primary_link', 'secondary_link',
                                    'tertiary_link', 'living_street', 'service', 'road'}
        self.rn = rn
        self.eid = 0

    def way(self, w):
        # forward: 0 backward:1 bi-dir: 2
        if 'highway' in w.tags and w.tags['highway'] in self.candi_highway_types:
            raw_eid = w.id
            full_coords = []
            for n in w.nodes:
                full_coords.append((n.lon, n.lat))
            # direction: 0-forward, 1-backward, 2-bi-directional
            if 'oneway' in w.tags:
                if w.tags['oneway'] != 'yes':
                    dir = 1
                else:
                    dir = 0
            else:
                dir = 2
            for i in range(len(full_coords)-1):
                coords = [full_coords[i], full_coords[i+1]]
                edge_attr = {'eid': self.eid, 'coords': coords, 'raw_eid': raw_eid, 'highway': w.tags['highway'],
                             'dir': dir}
                self.rn.add_edge(coords[0], coords[-1], **edge_attr)
                self.eid += 1


def compress_rn(raw_rn):
    print('raw rn #nodes:{}'.format(nx.number_of_nodes(raw_rn)))
    print('raw rn #edges:{}'.format(nx.number_of_edges(raw_rn)))
    compressed_rn = copy.deepcopy(raw_rn)
    modify_operations = []
    # 会不会有正着插入一遍，反着插入一遍，有两个modify_ops的情况？
    for node, degree in raw_rn.degree():
        if degree >= 3:
            roads = get_all_road_segments(node, raw_rn)
            for road in roads:
                if len(road) > 2:
                    modify_operations.append(road)
    print('nb modification roads:{}'.format(len(modify_operations)))
    for road in modify_operations:
        if not compressed_rn.has_edge(road[0], road[-1]):
            add_new_edge(road, 0, len(road)-1, compressed_rn)
        else:
            # if there is already a road segment between new_start_node and new_end_node,
            # we split the new edge to create two edges
            mid_idx = int(len(road) / 2.0)
            add_new_edge(road, 0, mid_idx, compressed_rn)
            add_new_edge(road, mid_idx, len(road)-1, compressed_rn)
    compressed_rn.remove_nodes_from(list(nx.isolates(compressed_rn)))
    print('compressed rn #nodes:{}'.format(nx.number_of_nodes(compressed_rn)))
    print('compressed rn #edges:{}'.format(nx.number_of_edges(compressed_rn)))
    return compressed_rn


def get_all_road_segments(int_node, g):
    all_road_segments = []
    for u, v in g.edges(int_node):
        first_adj_node = u if u != int_node else v
        # make sure a road would not be inserted for twice, this is achieved by only adding direction match edges
        if g[int_node][first_adj_node]['coords'][0] == int_node and \
                g[int_node][first_adj_node]['coords'][-1] == first_adj_node:
            road_segment = construct_road_segment(first_adj_node, g, [int_node, first_adj_node])
            all_road_segments.append(road_segment)
    return all_road_segments


def construct_road_segment(first_adj_node, g, seq):
    cur_node = first_adj_node
    while g.degree(cur_node) == 2:
        pre_node = seq[-2]
        for u, v in g.edges(cur_node):
            if u != pre_node and u != cur_node:
                next_node = u
                break
            elif v != pre_node and v != cur_node:
                next_node = v
                break
        seq.append(next_node)
        cur_node = next_node
    return seq


def add_new_edge(nodes, start_idx, end_idx, g):
    # end_idx is inclusive
    start_node = nodes[start_idx]
    end_node = nodes[end_idx]
    if not g.has_edge(nodes[start_idx], nodes[start_idx+1]):
        return
    first_edge = g[start_node][nodes[start_idx+1]]
    for i in range(start_idx, end_idx):
        if g.has_edge(nodes[i], nodes[i+1]):
            g.remove_edge(nodes[i], nodes[i+1])
    coords = []
    for pt_arr in nodes[start_idx:end_idx+1]:
        coords.append((pt_arr[0], pt_arr[1]))
    g.add_edge(start_node, end_node, eid=first_edge['eid'], highway=first_edge['highway'],
               raw_eid=first_edge['raw_eid'], dir=first_edge['dir'], coords=coords)


def to_std_rn(compressed_rn):
    std_rn = nx.DiGraph()
    avail_eid = max([compressed_rn[u][v]['eid'] for u, v, data in compressed_rn.edges(data=True)]) + 1
    for u, v, data in compressed_rn.edges(data=True):
        # direction: 0-forward, 1-backward, 2-bi-directional
        if data['dir'] == 0:
            coords = data['coords']
            edge_attr = {'eid': data['eid'], 'coords': data['coords'], 'raw_eid': data['raw_eid'],
                         'highway': data['highway']}
            std_rn.add_edge(coords[0], coords[-1], **edge_attr)
        elif data['dir'] == 1:
            reversed_coords = data['coords'].copy()
            reversed_coords.reverse()
            edge_attr = {'eid': data['eid'], 'coords': reversed_coords, 'raw_eid': data['raw_eid'],
                         'highway': data['highway']}
            std_rn.add_edge(reversed_coords[0], reversed_coords[-1], **edge_attr)
        else:
            coords = data['coords']
            edge_attr = {'eid': data['eid'], 'coords': data['coords'], 'raw_eid': data['raw_eid'],
                         'highway': data['highway']}
            std_rn.add_edge(coords[0], coords[-1], **edge_attr)

            reversed_coords = data['coords'].copy()
            reversed_coords.reverse()
            edge_attr = {'eid': avail_eid, 'coords': reversed_coords, 'raw_eid': data['raw_eid'],
                         'highway': data['highway']}
            std_rn.add_edge(reversed_coords[0], reversed_coords[-1], **edge_attr)
            avail_eid += 1
    return std_rn


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_path', help='the input path of the original osm data')
    parser.add_argument('--output_path', help='the output directory of the constructed road network')
    opt = parser.parse_args()
    print(opt)

    # first construct the undirected graph with direction attribute (split the edge to the minimum)
    raw_rn = nx.Graph()
    handler = OSM2RNHandler(raw_rn)
    handler.apply_file(opt.input_path, locations=True)
    # simplify vertices with degree 2
    compressed_rn = compress_rn(raw_rn)
    # construct the standard road network
    rn = to_std_rn(compressed_rn)
    store_shp(rn, opt.output_path)
