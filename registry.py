# Element registry. Used to fetch elements by their user-readable name.
element_registry = {}

def register_element(element):
    '''Adds an element to the registry.'''
    # FIXME: catch exception when .name doesn't exist in the element
    element_registry[element.name] = element

def get_element(name):
    '''Fetches an element from the registry.'''
    try:
        return element_registry[name]
    except KeyError:
        return None
