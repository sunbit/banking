class SomethingChangedError(Exception):
    def __init__(self, query):
        self.message = """
    No element was found matching the query:

        {query}
""".format(query=query)


class InteractionError(Exception):
    def __init__(self, action, element, suggestion):
        self.message = """
    An interaction error occurred while executing "{action}" on the element:

        {element}

    {suggestion}
""".format(action=action, element=element, suggestion=suggestion)
