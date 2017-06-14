# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from rdflib import Graph
from rdflib.namespace import RDF

from udata.rdf import (
    DCAT, DCT, HYDRA, SPDX, namespace_manager, guess_format, url_from_rdf
)
from udata.core.dataset.rdf import dataset_from_rdf

from . import BaseBackend, register

log = logging.getLogger(__name__)


# Attributes representing nested classes to be stored in the graph
# in order to have a complete graph
DCAT_NESTING = {
    DCAT.distribution: {
        SPDX.checksum: {}
    },
    DCT.temporal: {},
    DCT.spatial: {},
}

# Fix some misnamed properties
DCAT_NESTING[DCAT.distributions] = DCAT_NESTING[DCAT.distribution]

# Known pagination class and their next page property
KNOWN_PAGINATION = (
    (HYDRA.PartialCollectionView, HYDRA.next),
    (HYDRA.PagedCollection, HYDRA.nextPage)
)


def extract_graph(source, target, node, specs):
    for p, o in source.predicate_objects(node):
        target.add((node, p, o))
        if p in specs:
            extract_graph(source, target, o, specs[p])


@register
class DcatBackend(BaseBackend):
    name = 'dcat'
    display_name = 'DCAT'

    def initialize(self):
        '''List all datasets for a given ...'''
        fmt = guess_format(self.source.url)
        self.parse_graph(self.source.url, fmt)

    def parse_graph(self, url, fmt):
        graph = Graph(namespace_manager=namespace_manager)
        graph.parse(url, format=fmt)
        for id, data in self.dcat_datasets(graph):
            self.add_item(id, graph=data)

        for cls, prop in KNOWN_PAGINATION:
            if (None, RDF.type, cls) in graph:
                pagination = graph.value(predicate=RDF.type, object=cls)
                pagination = graph.resource(pagination)
                next_url = url_from_rdf(pagination, prop)
                if next_url:
                    self.parse_graph(next_url, fmt)
                break

    def dcat_datasets(self, graph):
        '''
        Extract DCAT dataset from a RDF graph.
        '''
        for node in graph.subjects(RDF.type, DCAT.Dataset):
            dcat_id = graph.value(node, DCT.identifier)
            subgraph = Graph(namespace_manager=namespace_manager)
            extract_graph(graph, subgraph, node, DCAT_NESTING)
            yield str(dcat_id), subgraph.serialize(format='json-ld',
                                                   indent=None)

    def process(self, item):
        graph = Graph(namespace_manager=namespace_manager)
        graph.parse(data=item.kwargs['graph'], format='json-ld')
        dataset = self.get_dataset(item.remote_id)
        dataset = dataset_from_rdf(graph, dataset)
        return dataset
