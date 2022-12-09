import json
from jsonpath_ng import jsonpath, parse


def transform(json_doc, json_path):
    data = json.loads(json_doc)
    jsonpath_expr = parse(json_path)
    result = [x.value for x in jsonpath_expr.find(data)]
    return json.dumps(result)