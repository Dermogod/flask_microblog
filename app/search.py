from flask import current_app

def add_to_index(index, model):
    '''add all searchable notes to search'''
    if not current_app.elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index = index, doc_type = index,
        id = model.id, body = payload)

def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index = index, doct_type = index,
        id = model.id)

def query_index(index, query, page, per_page):
    '''execute search query and paginate the 
    results depending on how many posts per page'''
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index = index, 
        doc_type = index,
        body = {'query': {'multi_match': {'query': query, 'fields': ['*']}},
                'from': (page - 1) * per_page, 'size': per_page 
                }
    )
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']