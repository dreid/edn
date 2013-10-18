"""
Things for working with parsley.
"""

from ometa.interp import TrampolinedGrammarInterpreter, _feed_me
from ometa.grammar import OMeta
from terml import nodes


# TODO: Remove these awful monkey patches when parsley released with
# https://github.com/python-parsley/parsley/pull/43

def _node_hash(node):
    return hash((nodes.Term, node.tag, node.data, node.args))

nodes.Term.__hash__ = _node_hash


def _tag_hash(tag):
    return hash((nodes.Tag, tag.name))

nodes.Tag.__hash__ = _tag_hash


def parseGrammar(definition, name='Grammar'):
    return OMeta(definition).parseGrammar(name)


# TODO: Remove when parsley released with
# https://github.com/python-parsley/parsley/pull/45
def _pumpInterpreter(interpFactory, dataChunk, interp=None):
    if interp is None:
        interp = interpFactory()
    while dataChunk:
        status = interp.receive(dataChunk)
        if status is _feed_me:
            break
        dataChunk = ''.join(interp.input.data[interp.input.position:])
        interp = interpFactory()
    if not interp.ended:
        interp.end()
    return interp


# TODO: Remove when parsley released with
# https://github.com/python-parsley/parsley/pull/45
def iterGrammar(grammar, bindings, rule, input_stream):
    """
    Repeatedly apply rule to an input stream, and yield matches.

    @param grammar: An ometa grammar.
    @param rule: The name of the rule to match.  Matches will be yielded.
    @param input_stream: The stream to read.  Will be read incrementally.
    """
    tokens = []  # Should really be an explicit queue.

    def append(token, error):
        if error.error:
            raise error
        tokens.append(token)

    def makeInterpreter():
        return TrampolinedGrammarInterpreter(
            grammar, rule, callback=append, globals=bindings)

    while True:
        data = input_stream.read()
        if not data:
            break
        _pumpInterpreter(makeInterpreter, data)
        for token in tokens:
            yield token
        tokens[:] = []
