import logging
from pymachine.utils import MachineGraph, jaccard

import networkx as nx
import networkx.algorithms.isomorphism as iso
import itertools

class SimFeatures:
    def __init__(self, cfg, section):
        self.batch = cfg.getboolean(section, 'batch')
        self.feats_to_get = cfg.get(section, 'sim_types').split('|')
        self.feats_dict = {
            'links_jaccard' : ['links_jaccard'],
            'entities_jaccard' : ['entities_jaccard'],
            'nodes_jaccard' : ['nodes_jaccard'],
            'links_contain' : ['links_contain'],
            'nodes_contain' : ['nodes_contain'],
            '0-connected' : ['0-connected', '0-connected_exp'],
            'is_antonym' : ['is_antonym'],
            'subgraphs' : ['subgraph_N']
        }

    def get_all_features(self, graph1, graph2):
        all_feats = dict()
        for f in self.feats_to_get:
            all_feats.update(self.get_feature_class(f, graph1, graph2))
        return all_feats

    def get_feature_class(self, feature_name, graph1, graph2):
        if feature_name == 'links_jaccard':
            return self.links_jaccard(graph1.links_expand, graph2.links_expand)
        elif feature_name == 'entities_jaccard':
            return self.entitiess_jaccard(graph1.links_expand, graph2.links_expand)
        elif feature_name == 'nodes_jaccard':
            return self.nodes_jaccard(graph1.nodes_expand, graph2.nodes_expand)
        elif feature_name == 'links_contain':
            return self.links_contain(graph1.name, graph1.links_expand, graph2.name, graph2.links_expand)
        elif feature_name == 'nodes_contain':
            return self.nodes_contain(graph1.name, graph1.nodes_expand, graph2.name, graph2.nodes_expand)
        elif feature_name == '0-connected':
            return self.zero_connected(graph1.name, graph1.links, graph1.links_expand,
                                       graph2.name, graph2.links, graph2.links_expand)
        elif feature_name == 'is_antonym':
            return self.is_antonym(graph1.name, graph1.nodes_expand, graph2.name, graph2.nodes_expand)
        elif feature_name == 'subgraphs':
            return self.subgraphs(graph1.machine, graph2.machine)
        else:
            return { feature_name : 0 }

    def links_jaccard(self, links1, links2):
        return { "links_jaccard" : jaccard(links1, links2)}

    def entitiess_jaccard(self, links1, links2):
        entities1 = filter(lambda l: "@" in l, links1)
        entities2 = filter(lambda l: "@" in l, links2)
        return {'entities_jaccard' : jaccard(entities1, entities2)}

    def nodes_jaccard(self, nodes1, nodes2):
        return { "nodes_jaccard" : jaccard(nodes1, nodes2)}

    def links_contain(self, name1, links1, name2, links2):
        val = -1
        if (self.contains(links1, name2) or
                self.contains(links2, name1)):
            val = 1
        return { "links_contain" : val}

    def nodes_contain(self, name1, nodes1, name2, nodes2):
        val = -1
        if (self.contains(nodes1, name2) or
                self.contains(nodes2, name1)):
            val = 1
        return { "nodes_contain" : val}

    def zero_connected(self, name1, links1, links1_expand, name2, links2, links2_expand):
        val = -1
        if name1 in links2 or name2 in links1:
            val = 1
        ret = { "0-connected" : val }
        val2 = -1
        if val == -1:
            if name1 in links2_expand or name2 in links1_expand:
                val2 = 1
        ret.update({ "0-connected_exp" : val2 })
        return ret

    def is_antonym(self, name1, nodes1, name2, nodes2):
        is_antonym = -1
        if ("lack_" + name1 in nodes2 or "lack_" + name2 in nodes1):
            is_antonym = 1
        return {"is_antonym" : is_antonym }

    def subgraphs(self, machine1, machine2):
        temp = SubGraphFeatures(machine1, machine2, 5)
        return temp.subgraph_dict

    def contains(self, links, name):
        for link in links:
            if link == name or (name in link and isinstance(link, tuple)):
                self.log('link "{0}" is/contains name "{1}"'.format(link, name))
                return True
        else:
            return False

    def uniform_similarities(self, s):
        temp_dict = dict()
        for sim_type in self.feats_to_get:
            for feat_type in self.feats_dict[sim_type]:
                temp_dict[feat_type] = s
        return temp_dict

    def zero_similarities(self):
        return self.uniform_similarities(0.0)

    def one_similarities(self):
        return self.uniform_similarities(1.0)

    def log(self, string):
        if not self.batch:
            logging.info(string)

class MachineInfo():
    def __init__(self, machine, nodes, nodes_expand, links, links_expand):
        self.name = machine.printname()
        self.machine = machine
        self.nodes = nodes
        self.links = links
        self.nodes_expand = nodes_expand
        self.links_expand = links_expand

class SubGraphFeatures():
    def __init__(self, machine1, machine2, max_depth):
        G1 = MachineGraph.create_from_machines([machine1], max_depth=max_depth)
        G2 = MachineGraph.create_from_machines([machine2], max_depth=max_depth)
        name1 = machine1.printname()
        name2 = machine2.printname()
        # print name1 + " " + name2

        # # GM = nx.algorithms.isomorphism.GraphMatcher(G1.G,G2.G)
        # GM = nx.algorithms.isomorphism.GraphMatcher(G1.G,G2.G, node_match=iso.categorical_node_match(['str_name'], ['']),
        #                                             edge_match=iso.numerical_edge_match(['color'], [-1]))
        #
        # print "\nSubgraphs START: " + name1 + " " + name2
        # for subgraph in GM.subgraph_isomorphisms_iter():
        #     print subgraph
        # print "Subgraphs END \n"


        # intersection = subgraphs1 & subgraphs2

        # if name1 == 'intelligent' or name2 == 'intelligent':
        #     for subg in subgraphs1:
        #         print "SUB_NODES"
        #         print subg.nodes(True)
        #     for subg in subgraphs2:
        #         print "SUB_NODES"
        #         print subg.nodes(True)

        # print "!!!!!!"
        # fish = (n for n in G1.G if G1.G.node[n]['str_name']=='intelligent')
        # print list(fish)

        self.subgraph_dict = dict()
        self.subgraph_dict["subgraph_N"] = 0

        subgraphs1 = self._get_subgraphs(G1.G, name1, 1)
        subgraphs2 = self._get_subgraphs(G2.G, name2, 1)

        # print "INTERSECTION: " + name1 + " " + name2
        for r in itertools.product(subgraphs1, subgraphs2):
            GM =  nx.algorithms.isomorphism.GraphMatcher(r[0], r[1],
                                                         node_match=iso.categorical_node_match(['str_name'], ['name']),
                                                         edge_match=iso.numerical_edge_match(['color'], [-1]))
            if GM.is_isomorphic():
                is_upper = False
                for n, d in r[0].nodes_iter(data=True):
                    if d['str_name'].isupper():
                        is_upper = True
                if not is_upper:
                    # print "ISOMORPHIC"
                    # print r[0].nodes(True)
                    # print r[1].nodes(True)
                    self.subgraph_dict["subgraph_N"] += 1
        # print "\n"


    def _get_subgraphs(self, graph, name, size=3):
        subgraphs = set()
        # print "\nSubgraphs START: " + name
        target = nx.complete_graph(size)
        for sub_nodes in itertools.combinations(graph.nodes(),len(target.nodes())):
            subg = graph.subgraph(sub_nodes)
            if nx.is_weakly_connected(subg):
                # print subg.edges()
                subgraphs.add(subg)
        # print "Subgraphs END \n"
        return subgraphs

def test():
    sf = SimFeatures()
    print sf.get_all_features()

if __name__ == "__main__":
    test()
