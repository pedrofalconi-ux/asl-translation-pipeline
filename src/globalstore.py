# Global store. Used for whenever data needs to be shared between different
# elements.
global_store = {}

def add_to_store(key, value):
    '''Adds or updates data in the global store.'''
    global_store[key] = value

def fetch_from_store(key):
    '''Fetches data from the global store.'''
    try:
        return global_store[key]
    except KeyError:
        return None
