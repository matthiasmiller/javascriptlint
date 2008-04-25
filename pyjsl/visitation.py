# vim: ts=4 sw=4 expandtab
""" This is an abstract module for visiting specific nodes. This is useed to
traverse the tree to generate warnings.
"""

def visit(event, *args):
    """ This decorator is used to indicate which nodes the function should
    examine. The function should accept (self, node) and return the relevant
    node or None. """
    def _decorate(fn):
        fn._visit_event = event
        fn._visit_nodes = args
        return fn
    return _decorate

def make_visitors(klasses):
    """ Searches klasses for all member functions decorated with @visit and
    returns a dictionary that maps from node type to visitor function. """
    visitors = {}

    # Intantiate an instance of each class
    for klass in klasses:
        if klass.__name__.lower() != klass.__name__:
            raise ValueError, 'class names must be lowercase'
        if not klass.__doc__:
            raise ValueError, 'missing docstring on class'

        # Look for functions with the "_visit_nodes" property.
        visitor = klass()
        for func in [getattr(visitor, name) for name in dir(visitor)]:
            event_visitors = None
            for node_kind in getattr(func, '_visit_nodes', ()):
                # Group visitors by event (e.g. push vs pop)
                if not event_visitors:
                    if not func._visit_event in visitors:
                        visitors[func._visit_event] = {}
                    event_visitors = visitors[func._visit_event]

                # Map from node_kind to the function
                if not node_kind in visitors:
                    event_visitors[node_kind] = []
                event_visitors[node_kind].append(func)
    return visitors

