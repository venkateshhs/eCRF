from pyshacl import validate
from rdflib import Graph
from typing import Tuple

# TODO
"""Is this really necessary if we do all validations at the frontend ???? check this"""







def validate_data_with_shape(data_graph: str, shape_graph: str) -> Tuple[bool, str]:
    """
    Validate data using a SHACL shape.

    :param data_graph: RDF graph as a string (e.g., Turtle format).
    :param shape_graph: SHACL shape graph as a string (e.g., Turtle format).
    :return: Tuple (conforms, result_text).
    """
    conforms, _, results_text = validate(
        data_graph=Graph().parse(data=data_graph, format="turtle"),
        shacl_graph=Graph().parse(data=shape_graph, format="turtle"),
        inference="rdfs",  # Optional
        debug=True,
    )
    return conforms, results_text
